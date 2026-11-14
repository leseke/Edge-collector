"""Deterministic virtual schedule for expected MRI source-check windows.

This module never starts a scheduler or a collector. It derives past/current
expected windows from an explicit cadence and an as-of instant.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


UTC = timezone.utc
_REQUIRED_CADENCE_KEYS = {
    "schedule_id", "timezone", "interval_minutes", "lookback_days",
}


def _parse_instant(value):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("as_of must be a valid ISO-8601 timestamp") from exc
    else:
        raise ValueError("as_of must be an aware datetime or ISO-8601 string")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("as_of must include a timezone")
    return parsed.astimezone(UTC)


def _validate_cadence(cadence):
    if not isinstance(cadence, dict) or set(cadence) != _REQUIRED_CADENCE_KEYS:
        raise ValueError("cadence must define exactly schedule_id, timezone, interval_minutes and lookback_days")
    schedule_id = cadence["schedule_id"]
    zone_name = cadence["timezone"]
    interval = cadence["interval_minutes"]
    lookback = cadence["lookback_days"]
    if not isinstance(schedule_id, str) or not schedule_id.strip():
        raise ValueError("schedule_id must be a non-empty string")
    if not isinstance(zone_name, str) or not zone_name.strip():
        raise ValueError("timezone must be a non-empty IANA timezone")
    try:
        zone = ZoneInfo(zone_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("timezone must be a known IANA timezone") from exc
    if isinstance(interval, bool) or not isinstance(interval, int):
        raise ValueError("interval_minutes must be an integer")
    if interval < 1 or interval > 1440 or 1440 % interval:
        raise ValueError("interval_minutes must be a positive divisor of 1440")
    if isinstance(lookback, bool) or not isinstance(lookback, int):
        raise ValueError("lookback_days must be an integer")
    if lookback < 0 or lookback > 366:
        raise ValueError("lookback_days must be between 0 and 366")
    return schedule_id, zone_name, zone, interval, lookback


def _valid_local_instants(local_naive, zone):
    """Return zero, one or two UTC instants for a local wall-clock time.

    Non-existent wall times during a spring-forward transition are skipped.
    Both folds of an ambiguous fall-back wall time are retained.
    """
    instants = set()
    for fold in (0, 1):
        candidate = local_naive.replace(tzinfo=zone, fold=fold)
        utc_instant = candidate.astimezone(UTC)
        round_trip = utc_instant.astimezone(zone)
        if round_trip.replace(tzinfo=None) == local_naive:
            instants.add(utc_instant)
    return sorted(instants)


def _source_mapping(source_plan, source_id_map):
    if not isinstance(source_plan, dict):
        raise ValueError("source_plan must be an object")
    enabled = source_plan.get("expected_sources")
    disabled = source_plan.get("not_scheduled_sources", [])
    providers = source_plan.get("providers")
    if not isinstance(enabled, list) or not isinstance(disabled, list):
        raise ValueError("source_plan source lists are invalid")
    if not isinstance(providers, dict):
        raise ValueError("source_plan providers must be an object")
    for values, label in ((enabled, "enabled"), (disabled, "disabled")):
        if any(not isinstance(item, str) or not item.strip() for item in values):
            raise ValueError(f"{label} source check IDs must be non-empty strings")
        if len(values) != len(set(values)):
            raise ValueError(f"{label} source check IDs must be unique")
    if set(enabled) & set(disabled):
        raise ValueError("a source check cannot be both enabled and disabled")
    if any(check_id not in providers for check_id in enabled + disabled):
        raise ValueError("every source check ID must have a provider")
    if any(not isinstance(providers[item], str) or not providers[item].strip()
           for item in enabled + disabled):
        raise ValueError("source providers must be non-empty strings")
    if source_id_map is None:
        source_id_map = {}
    if not isinstance(source_id_map, dict):
        raise ValueError("source_id_map must be an object")
    if any(key not in enabled for key in source_id_map):
        raise ValueError("source_id_map may only map enabled source check IDs")
    mapping = {}
    for check_id in enabled:
        source_id = source_id_map.get(check_id, check_id)
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("mapped source IDs must be non-empty strings")
        mapping[check_id] = source_id
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("enabled source checks must map to unique source IDs")
    return mapping, list(disabled)


def build_expected_windows(cadence, source_plan, as_of, source_id_map=None):
    """Build deterministic expected windows without running any collection.

    Cadence is explicit and contains exactly:
      schedule_id, timezone (IANA), interval_minutes, lookback_days.

    Source-plan check IDs are mapped to source IDs using source_id_map;
    omitted mappings use the stable identity mapping. Disabled checks are
    reported separately and never enter expected_sources.

    With no cadence, no schedule is inferred and the result remains UNKNOWN.
    """
    cut = _parse_instant(as_of)
    mapping, disabled = _source_mapping(source_plan, source_id_map)
    if cadence is None:
        return {
            "schedule_status": "UNKNOWN",
            "schedule_reason": "CADENCE_NOT_CONFIGURED",
            "as_of": cut.isoformat().replace("+00:00", "Z"),
            "timezone": None,
            "expected_windows": [],
            "source_mapping": mapping,
            "not_scheduled_sources": disabled,
        }

    schedule_id, zone_name, zone, interval, lookback = _validate_cadence(cadence)
    if not mapping:
        return {
            "schedule_status": "UNKNOWN",
            "schedule_reason": "NO_ENABLED_SOURCES",
            "as_of": cut.isoformat().replace("+00:00", "Z"),
            "timezone": zone_name,
            "expected_windows": [],
            "source_mapping": mapping,
            "not_scheduled_sources": disabled,
        }

    local_cut = cut.astimezone(zone)
    first_day = local_cut.date() - timedelta(days=lookback)
    last_day = local_cut.date()
    windows = []
    seen_ids = set()
    current_day = first_day
    while current_day <= last_day:
        midnight = datetime.combine(current_day, time.min)
        for minute in range(0, 1440, interval):
            local_wall_time = midnight + timedelta(minutes=minute)
            for instant in _valid_local_instants(local_wall_time, zone):
                if instant > cut:
                    continue
                window_id = f"{schedule_id}:{instant.strftime('%Y%m%dT%H%M%SZ')}"
                if window_id in seen_ids:
                    raise ValueError("duplicate deterministic window ID")
                seen_ids.add(window_id)
                windows.append({
                    "window_id": window_id,
                    "scheduled_at": instant.isoformat().replace("+00:00", "Z"),
                    "expected_sources": sorted(mapping.values()),
                })
        current_day += timedelta(days=1)

    windows.sort(key=lambda item: item["scheduled_at"])
    return {
        "schedule_status": "SCHEDULED",
        "schedule_reason": None,
        "as_of": cut.isoformat().replace("+00:00", "Z"),
        "timezone": zone_name,
        "interval_minutes": interval,
        "lookback_days": lookback,
        "expected_windows": windows,
        "source_mapping": mapping,
        "not_scheduled_sources": disabled,
    }
