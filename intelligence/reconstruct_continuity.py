"""Conservative reconstruction of independently scheduled source checks."""
from __future__ import annotations

from datetime import datetime, timezone

from intelligence.remote_journal_simulator import InMemoryRemoteJournal

SOURCE_OUTCOMES = {"OBSERVED", "NO_REACTION_OBSERVED", "SOURCE_FAILED"}


def _instant(value):
    if not isinstance(value, str):
        raise ValueError("timestamp ISO requis")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ValueError("timestamp ISO invalide") from exc
    if parsed.tzinfo is None:
        raise ValueError("timezone obligatoire")
    return parsed.astimezone(timezone.utc)


def _iso(value):
    return value.isoformat().replace("+00:00", "Z")


def verify_run_history(run_events):
    """Verify the append-only STARTED/FINISHED journal by replay."""
    if not isinstance(run_events, list):
        raise ValueError("run_events doit être une liste")
    journal = InMemoryRemoteJournal()
    starts, finishes = {}, set()
    for event in run_events:
        journal.append_if_head(journal.head, event)
        key = (event["run_id"], event["attempt"])
        if event["event_type"] == "STARTED":
            starts[key] = event
        else:
            finishes.add(key)
    return {"started": starts, "finished": finishes, "verified": True}


def reconstruct_windows(expected_windows, run_events, source_outcomes, as_of):
    """Reconstruct windows from scheduler expectations and per-source outcomes.

    expected_windows: {window_id, scheduled_at, expected_sources:[source ids]}.
    source_outcomes: {window_id, run_id, attempt, source_id, outcome, occurred_at}.
    Each expected source must have exactly one outcome for a fully known window.
    """
    if not isinstance(expected_windows, list) or not isinstance(source_outcomes, list):
        raise ValueError("fenêtres et résultats doivent être des listes")
    cut = _instant(as_of)
    history = verify_run_history(run_events)
    starts = history["started"]

    windows, schedule_seen = {}, set()
    for item in expected_windows:
        required = {"window_id", "scheduled_at", "expected_sources"}
        if not isinstance(item, dict) or set(item) != required:
            raise ValueError("fenêtre attendue invalide")
        window_id, sources = item["window_id"], item["expected_sources"]
        if not isinstance(window_id, str) or not window_id.strip() or window_id in windows:
            raise ValueError("window_id invalide ou dupliqué")
        if (not isinstance(sources, list) or not sources
                or any(not isinstance(s, str) or not s.strip() for s in sources)
                or len(set(sources)) != len(sources)):
            raise ValueError("expected_sources invalide")
        scheduled = _instant(item["scheduled_at"])
        if scheduled in schedule_seen:
            raise ValueError("horaires de fenêtres dupliqués")
        schedule_seen.add(scheduled)
        if scheduled <= cut:
            windows[window_id] = {
                "scheduled": scheduled, "expected_sources": set(sources)
            }

    outcomes_by_window = {}
    for item in source_outcomes:
        required = {"window_id", "run_id", "attempt", "source_id", "outcome", "occurred_at"}
        if not isinstance(item, dict) or set(item) != required:
            raise ValueError("résultat source invalide")
        window_id = item["window_id"]
        if window_id not in windows:
            raise ValueError("résultat lié à une fenêtre inconnue ou future")
        if (not isinstance(item["run_id"], str) or not item["run_id"].strip()
                or isinstance(item["attempt"], bool) or not isinstance(item["attempt"], int)
                or item["attempt"] < 1):
            raise ValueError("identité de run invalide")
        source_id = item["source_id"]
        window = windows[window_id]
        if source_id not in window["expected_sources"]:
            raise ValueError("source non prévue pour cette fenêtre")
        bucket = outcomes_by_window.setdefault(window_id, {})
        if source_id in bucket:
            raise ValueError("résultat source dupliqué pour cette fenêtre")
        if item["outcome"] not in SOURCE_OUTCOMES:
            raise ValueError("outcome invalide")
        key = (item["run_id"], item["attempt"])
        if key not in starts:
            raise ValueError("résultat sans exécution STARTED vérifiée")
        start_event = starts[key]
        scheduled_at = start_event["payload"].get("scheduled_at")
        if not scheduled_at or _instant(scheduled_at) != window["scheduled"]:
            raise ValueError("résultat lié à une exécution planifiée différente")
        occurred = _instant(item["occurred_at"])
        started_at = _instant(start_event["occurred_at_utc"])
        if occurred < started_at or occurred > cut:
            raise ValueError("résultat hors de la période d'exécution")
        finish_event = next((
            event for event in run_events
            if event["run_id"] == item["run_id"]
            and event["attempt"] == item["attempt"]
            and event["event_type"] == "FINISHED"
        ), None)
        if finish_event and occurred > _instant(finish_event["occurred_at_utc"]):
            raise ValueError("résultat postérieur à la fin de l'exécution")
        bucket[source_id] = item

    started_by_schedule = {}
    for key, event in starts.items():
        scheduled_at = event["payload"].get("scheduled_at")
        if scheduled_at:
            started_by_schedule.setdefault(_instant(scheduled_at), []).append(key)

    rows = []
    source_counts = {status: 0 for status in sorted(SOURCE_OUTCOMES)}
    for window_id, window in sorted(windows.items(), key=lambda pair: pair[1]["scheduled"]):
        bucket = outcomes_by_window.get(window_id, {})
        matching_runs = started_by_schedule.get(window["scheduled"], [])
        run_keys = {(item["run_id"], item["attempt"]) for item in bucket.values()}
        if len(run_keys) > 1:
            raise ValueError("une fenêtre ne peut pas agréger plusieurs exécutions")
        run_key = next(iter(run_keys), None)
        missing_sources = sorted(window["expected_sources"] - set(bucket))
        run_finished = run_key in history["finished"] if run_key else False
        if not bucket and not matching_runs:
            status = "MISSED"
        elif not run_key:
            status = "UNKNOWN"
        elif missing_sources or not run_finished:
            status = "UNKNOWN"
        else:
            outcomes = [item["outcome"] for item in bucket.values()]
            if all(value == "SOURCE_FAILED" for value in outcomes):
                status = "SOURCE_FAILED"
            elif "SOURCE_FAILED" in outcomes:
                status = "DEGRADED"
            elif "OBSERVED" in outcomes:
                status = "OBSERVED"
            else:
                status = "NO_REACTION_OBSERVED"
        for item in bucket.values():
            source_counts[item["outcome"]] += 1
        rows.append({
            "window_id": window_id,
            "scheduled_at": _iso(window["scheduled"]),
            "status": status,
            "run_id": run_key[0] if run_key else None,
            "source_outcomes": [
                {"source_id": source_id, "outcome": item["outcome"],
                 "evidence_at": _iso(_instant(item["occurred_at"]))}
                for source_id, item in sorted(bucket.items())
            ],
            "missing_sources": missing_sources,
        })

    window_counts = {status: sum(row["status"] == status for row in rows)
                     for status in ("OBSERVED", "NO_REACTION_OBSERVED",
                                    "SOURCE_FAILED", "DEGRADED", "MISSED", "UNKNOWN")}
    total_windows = len(rows)
    total_source_checks = sum(len(window["expected_sources"]) for window in windows.values())
    attempted_source_checks = sum(source_counts.values())
    successful_source_checks = source_counts["OBSERVED"] + source_counts["NO_REACTION_OBSERVED"]
    has_unknown = window_counts["UNKNOWN"] > 0
    has_missed = window_counts["MISSED"] > 0
    has_failures = source_counts["SOURCE_FAILED"] > 0
    continuity = (
        "UNKNOWN" if total_windows == 0 or has_unknown else
        "GAP" if has_missed else
        "DEGRADED" if has_failures else
        "CONTINUOUS"
    )
    return {
        "journal_status": "VERIFIED",
        "continuity_status": continuity,
        "as_of": _iso(cut),
        "expected_windows": total_windows,
        "window_counts": window_counts,
        "source_counts": source_counts,
        "expected_source_checks": total_source_checks,
        "completed_source_checks": attempted_source_checks,
        "observation_coverage_ratio": (
            round(successful_source_checks / total_source_checks, 4)
            if total_source_checks and not has_unknown else None
        ),
        "attempt_coverage_ratio": (
            round(attempted_source_checks / total_source_checks, 4)
            if total_source_checks and not has_unknown else None
        ),
        "windows": rows,
    }
