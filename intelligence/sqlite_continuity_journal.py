"""SQLite adapter for explicit MRI scheduled-run journal events.

No scheduler, connector, network call, or collector integration is activated.
The caller supplies the already-validated expected-window registry.
"""
from __future__ import annotations

from intelligence.remote_journal_simulator import make_event
from intelligence.scheduled_run_context import resolve_scheduled_run_context


class SQLiteContinuityJournal:
    """Thin adapter over storage.append_run_event/list_run_events.

    storage.py keys lifecycle rows by run_id, so run_id must uniquely identify
    one attempt (as collect.py's GitHub run/attempt suffix currently does).
    """

    def __init__(self, append_event, list_events):
        if not callable(append_event) or not callable(list_events):
            raise ValueError("append_event and list_events must be callable")
        self._append_event = append_event
        self._list_events = list_events

    def _history(self, run_id, attempt):
        rows = self._list_events(run_id)
        events = []
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"event_type", "occurred_at", "payload"}:
                raise ValueError("SQLite run event row is malformed")
            events.append(make_event(
                run_id, attempt, row["event_type"], row["occurred_at"], row["payload"]
            ))
        return events

    def start(self, context, trigger="schedule", occurred_at=None):
        if trigger != "schedule":
            raise ValueError("scheduled context requires schedule trigger")
        self._append_event(context.run_id, "STARTED", {
            "trigger": trigger,
            "scheduled_at": context.scheduled_at,
        }, occurred_at)

    def record_source_result(self, context, expected_windows, connector_result,
                             source_id, occurred_at=None):
        history = self._history(context.run_id, context.attempt)
        resolved = resolve_scheduled_run_context(
            expected_windows, history, context.run_id, context.attempt, context.window_id
        )
        if resolved != context:
            raise ValueError("resolved scheduled context differs from supplied context")
        payload = context.source_result_payload(connector_result, source_id)
        self._append_event(context.run_id, "SOURCE_RESULT", payload, occurred_at)
        return payload

    def finish(self, context, payload, occurred_at=None):
        history = self._history(context.run_id, context.attempt)
        # Validate lifecycle before allowing FINISHED. Source results may already exist.
        starts = [event for event in history if event["event_type"] == "STARTED"]
        finishes = [event for event in history if event["event_type"] == "FINISHED"]
        if len(starts) != 1 or finishes:
            raise ValueError("FINISHED requires exactly one prior STARTED event and no prior FINISHED")
        resolved = resolve_scheduled_run_context(
            [{"window_id": context.window_id,
              "scheduled_at": context.scheduled_at,
              "expected_sources": list(context.expected_sources)}],
            history, context.run_id, context.attempt, context.window_id
        )
        if resolved != context:
            raise ValueError("resolved scheduled context differs from supplied context")
        if not isinstance(payload, dict) or payload.get("run_status") not in {
            "OK", "PARTIAL", "EMPTY", "FAILED"
        }:
            raise ValueError("FINISHED payload requires a valid run_status")
        self._append_event(context.run_id, "FINISHED", payload, occurred_at)
