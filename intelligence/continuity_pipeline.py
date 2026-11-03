"""Safe orchestration of virtual MRI schedules and continuity reconstruction."""
from __future__ import annotations

from datetime import datetime, timezone

from intelligence.reconstruct_continuity import (
    reconstruct_windows,
    verify_run_history,
)
from intelligence.window_schedule import build_expected_windows


def _utc(value):
    if not isinstance(value, str):
        raise ValueError("timestamp ISO requis")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp ISO invalide") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timezone obligatoire")
    return parsed.astimezone(timezone.utc)


def _unknown_schedule_report(schedule, reason):
    windows = schedule["expected_windows"]
    return {
        "schedule_status": schedule["schedule_status"],
        "schedule_reason": schedule["schedule_reason"],
        "journal_status": "UNKNOWN",
        "continuity_status": "UNKNOWN",
        "as_of": schedule["as_of"],
        "unknown_reason": reason,
        "expected_windows": len(windows),
        "window_counts": {
            "OBSERVED": 0,
            "NO_REACTION_OBSERVED": 0,
            "SOURCE_FAILED": 0,
            "DEGRADED": 0,
            "MISSED": 0,
            "UNKNOWN": len(windows),
        },
        "source_counts": {
            "OBSERVED": 0,
            "NO_REACTION_OBSERVED": 0,
            "SOURCE_FAILED": 0,
        },
        "expected_source_checks": sum(
            len(item["expected_sources"]) for item in windows
        ),
        "completed_source_checks": 0,
        "observation_coverage_ratio": None,
        "attempt_coverage_ratio": None,
        "windows": [
            {
                "window_id": item["window_id"],
                "scheduled_at": item["scheduled_at"],
                "status": "UNKNOWN",
                "run_id": None,
                "source_outcomes": [],
                "missing_sources": list(item["expected_sources"]),
            }
            for item in windows
        ],
    }


def build_continuity_report(
    cadence,
    source_plan,
    as_of,
    run_events,
    source_outcomes=None,
    source_id_map=None,
):
    """Build a schedule and reconstruct continuity without running collectors.

    Missing cadence or no enabled source checks stays UNKNOWN. Unscheduled
    STARTED events inside the requested schedule horizon are not assigned to
    arbitrary windows: otherwise they could be misreported as missed checks.
    """
    schedule = build_expected_windows(
        cadence, source_plan, as_of, source_id_map=source_id_map
    )
    if schedule["schedule_status"] != "SCHEDULED":
        return _unknown_schedule_report(
            schedule, schedule["schedule_reason"] or "SCHEDULE_UNAVAILABLE"
        )

    # Verify journal integrity before making any continuity claim.
    verify_run_history(run_events)
    cut = _utc(schedule["as_of"])
    first_scheduled = min(
        _utc(item["scheduled_at"]) for item in schedule["expected_windows"]
    )
    unlinked_runs = []
    for event in run_events:
        if event.get("event_type") != "STARTED":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("payload STARTED invalide")
        scheduled_at = payload.get("scheduled_at")
        if scheduled_at is None:
            occurred = _utc(event["occurred_at_utc"])
            if first_scheduled <= occurred <= cut:
                unlinked_runs.append(event)

    report = reconstruct_windows(
        schedule["expected_windows"],
        run_events,
        source_outcomes=source_outcomes,
        as_of=schedule["as_of"],
    )
    report.update({
        "schedule_status": schedule["schedule_status"],
        "schedule_reason": schedule["schedule_reason"],
        "timezone": schedule["timezone"],
        "interval_minutes": schedule["interval_minutes"],
        "lookback_days": schedule["lookback_days"],
        "not_scheduled_sources": schedule["not_scheduled_sources"],
    })

    if unlinked_runs:
        # An unlinked run could correspond to any unmatched scheduled window.
        # Never convert that ambiguity into a definitive MISSED outcome.
        for row in report["windows"]:
            if row["status"] == "MISSED":
                row["status"] = "UNKNOWN"
        report["window_counts"] = {
            status: sum(row["status"] == status for row in report["windows"])
            for status in (
                "OBSERVED", "NO_REACTION_OBSERVED", "SOURCE_FAILED",
                "DEGRADED", "MISSED", "UNKNOWN",
            )
        }
        report["continuity_status"] = "UNKNOWN"
        report["observation_coverage_ratio"] = None
        report["attempt_coverage_ratio"] = None
        report["unknown_reason"] = "UNLINKED_RUN_HISTORY"

    return report

def build_local_sqlite_continuity_report(
    cadence, source_plan, as_of, journal, source_id_map=None
):
    """Replay the accessible local SQLite journal without claiming durable coverage.

    A runner-local SQLite database may be absent or incomplete after runner
    replacement. Positive recorded observations remain visible, but missing
    windows are downgraded to UNKNOWN and coverage ratios are suppressed.
    """
    read_history = getattr(journal, "read_history", None)
    if not callable(read_history):
        raise ValueError("journal must expose read_history()")
    run_events = read_history()
    report = build_continuity_report(
        cadence, source_plan, as_of, run_events, source_id_map=source_id_map
    )
    for row in report["windows"]:
        if row["status"] == "MISSED":
            row["status"] = "UNKNOWN"
    report["window_counts"] = {
        status: sum(row["status"] == status for row in report["windows"])
        for status in (
            "OBSERVED", "NO_REACTION_OBSERVED", "SOURCE_FAILED",
            "DEGRADED", "MISSED", "UNKNOWN",
        )
    }
    report["journal_status"] = "DEGRADED" if run_events else "UNKNOWN"
    report["continuity_status"] = "UNKNOWN"
    report["observation_coverage_ratio"] = None
    report["attempt_coverage_ratio"] = None
    report["journal_backend"] = "SQLITE_LOCAL"
    report["journal_completeness"] = "NOT_PROVEN"
    report["unknown_reason"] = "LOCAL_SQLITE_HISTORY_NOT_DURABLE"
    return report
