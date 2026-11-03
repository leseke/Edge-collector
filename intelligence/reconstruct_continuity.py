"""Reconstruct expected surveillance windows from independent schedule and evidence streams.

Execution events prove that a collector ran; they do not prove market observation.
Only explicit source outcomes can classify a window as observed/no-reaction/source-failed.
"""
from __future__ import annotations

from datetime import datetime, timezone

from intelligence.remote_journal_simulator import (
    InMemoryRemoteJournal, JournalIntegrityError,
)


OUTCOMES = {"OBSERVED", "NO_REACTION_OBSERVED", "SOURCE_FAILED"}


def _instant(value):
    if not isinstance(value, str):
        raise ValueError("timestamp ISO requis")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp ISO invalide") from exc
    if parsed.tzinfo is None:
        raise ValueError("timezone obligatoire")
    return parsed.astimezone(timezone.utc)


def _iso(value):
    return value.isoformat().replace("+00:00", "Z")


def verify_run_history(run_events):
    """Replay a restored run journal; return run identities and start metadata.

    A STARTED without FINISHED is a valid interrupted run, but cannot prove
    that collection completed. Malformed or reordered history is rejected.
    """
    if not isinstance(run_events, list):
        raise ValueError("run_events doit être une liste")
    journal = InMemoryRemoteJournal()
    starts = {}
    finishes = set()
    for event in run_events:
        journal.append_if_head(journal.head, event)
        key = (event["run_id"], event["attempt"])
        if event["event_type"] == "STARTED":
            starts[key] = event
        else:
            finishes.add(key)
    return {
        "started": starts,
        "finished": finishes,
        "verified": True,
    }


def reconstruct_windows(expected_windows, run_events, source_outcomes, as_of):
    """Classify each independently scheduled window without inventing coverage.

    expected_windows: {window_id, scheduled_at}, produced by a scheduler.
    run_events: restored append-only STARTED/FINISHED history.
    source_outcomes: {window_id, run_id, attempt, source_id, outcome, occurred_at}.
    """
    if not isinstance(expected_windows, list) or not isinstance(source_outcomes, list):
        raise ValueError("fenêtres et résultats doivent être des listes")
    cut = _instant(as_of)
    history = verify_run_history(run_events)
    starts = history["started"]

    windows = {}
    for item in expected_windows:
        if not isinstance(item, dict) or set(item) != {"window_id", "scheduled_at"}:
            raise ValueError("fenêtre attendue invalide")
        window_id = item["window_id"]
        if not isinstance(window_id, str) or not window_id.strip() or window_id in windows:
            raise ValueError("window_id invalide ou dupliqué")
        scheduled = _instant(item["scheduled_at"])
        if scheduled <= cut:
            windows[window_id] = {"scheduled": scheduled, "status": None}

    outcome_by_window = {}
    for item in source_outcomes:
        required = {"window_id", "run_id", "attempt", "source_id", "outcome", "occurred_at"}
        if not isinstance(item, dict) or set(item) != required:
            raise ValueError("résultat source invalide")
        window_id = item["window_id"]
        if window_id not in windows:
            raise ValueError("résultat lié à une fenêtre inconnue ou future")
        if window_id in outcome_by_window:
            raise ValueError("plusieurs résultats pour une même fenêtre non agrégés")
        key = (item["run_id"], item["attempt"])
        if key not in starts:
            raise ValueError("résultat sans exécution STARTED vérifiée")
        if item["outcome"] not in OUTCOMES:
            raise ValueError("outcome invalide")
        if not isinstance(item["source_id"], str) or not item["source_id"].strip():
            raise ValueError("source_id invalide")
        occurred = _instant(item["occurred_at"])
        if occurred < windows[window_id]["scheduled"] or occurred > cut:
            raise ValueError("résultat hors de sa fenêtre temporelle")
        outcome_by_window[window_id] = item

    # A run whose scheduled_at matches a window but has no source outcome is
    # UNKNOWN: execution began, but the market evidence cannot be reconstructed.
    started_by_schedule = {}
    for key, event in starts.items():
        scheduled_at = event["payload"].get("scheduled_at")
        if scheduled_at:
            scheduled = _instant(scheduled_at)
            started_by_schedule.setdefault(scheduled, []).append(key)

    rows = []
    for window_id, window in sorted(windows.items(), key=lambda pair: pair[1]["scheduled"]):
        result = outcome_by_window.get(window_id)
        if result:
            status = result["outcome"]
            run_key = (result["run_id"], result["attempt"])
            finished = run_key in history["finished"]
            if not finished:
                status = "UNKNOWN"
            rows.append({
                "window_id": window_id,
                "scheduled_at": _iso(window["scheduled"]),
                "status": status,
                "run_id": result["run_id"],
                "source_id": result["source_id"],
                "evidence_at": _iso(_instant(result["occurred_at"])),
            })
            continue
        matching_runs = started_by_schedule.get(window["scheduled"], [])
        if matching_runs:
            status = "UNKNOWN" if any(key not in history["finished"] for key in matching_runs) else "MISSED"
        else:
            status = "MISSED"
        rows.append({
            "window_id": window_id,
            "scheduled_at": _iso(window["scheduled"]),
            "status": status,
            "run_id": None,
            "source_id": None,
            "evidence_at": None,
        })

    counts = {status: sum(row["status"] == status for row in rows)
              for status in ("OBSERVED", "NO_REACTION_OBSERVED", "SOURCE_FAILED", "MISSED", "UNKNOWN")}
    total = len(rows)
    classified = counts["OBSERVED"] + counts["NO_REACTION_OBSERVED"] + counts["SOURCE_FAILED"]
    return {
        "journal_status": "VERIFIED",
        "continuity_status": "UNKNOWN" if counts["UNKNOWN"] else ("GAP" if counts["MISSED"] else "CONTINUOUS"),
        "as_of": _iso(cut),
        "expected_windows": total,
        "classified_windows": classified,
        "coverage_ratio": round(classified / total, 4) if total else None,
        "counts": counts,
        "windows": rows,
    }
