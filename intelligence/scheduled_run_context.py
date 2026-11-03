"""Explicit, validated association between one execution and one MRI window.

This contract is deliberately separate from collect.py: no scheduler is started,
no timestamp is inferred from process start, and no connector is invoked.
"""
from __future__ import annotations

from dataclasses import dataclass

from connectors.result import OBSERVED, NO_REACTION_OBSERVED, SOURCE_FAILED
from intelligence.reconstruct_continuity import verify_run_history


_EXECUTABLE_OUTCOMES = {OBSERVED, NO_REACTION_OBSERVED, SOURCE_FAILED}


def _utc(value):
    from datetime import datetime, timezone

    if not isinstance(value, str):
        raise ValueError("scheduled_at must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("scheduled_at must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("scheduled_at must include a timezone")
    return parsed.astimezone(timezone.utc)


def _canonical_utc(value):
    return _utc(value).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ScheduledRunContext:
    """Immutable proof inputs for a single run/window association."""

    window_id: str
    scheduled_at: str
    run_id: str
    attempt: int
    expected_sources: tuple[str, ...]

    def __post_init__(self):
        if not isinstance(self.window_id, str) or not self.window_id.strip():
            raise ValueError("window_id must be non-empty")
        if not isinstance(self.run_id, str) or not self.run_id.strip():
            raise ValueError("run_id must be non-empty")
        if isinstance(self.attempt, bool) or not isinstance(self.attempt, int) or self.attempt < 1:
            raise ValueError("attempt must be a positive integer")
        if not isinstance(self.expected_sources, tuple) or not self.expected_sources:
            raise ValueError("expected_sources must be a non-empty tuple")
        if any(not isinstance(item, str) or not item.strip() for item in self.expected_sources):
            raise ValueError("expected source IDs must be non-empty strings")
        if len(set(self.expected_sources)) != len(self.expected_sources):
            raise ValueError("expected source IDs must be unique")
        object.__setattr__(self, "scheduled_at", _canonical_utc(self.scheduled_at))

    def source_result_payload(self, connector_result, source_id):
        """Build a minimal SOURCE_RESULT payload for an expected source only."""
        if source_id not in self.expected_sources:
            raise ValueError("source_id is not expected for this window")
        if connector_result.status not in _EXECUTABLE_OUTCOMES:
            raise ValueError("only completed execution outcomes may be journaled")
        payload = connector_result.to_event_payload(self.window_id, source_id)
        if set(payload) != {"window_id", "source_id", "outcome"}:
            raise ValueError("connector result payload violates the journal allowlist")
        return payload


def resolve_scheduled_run_context(expected_windows, run_events, run_id, attempt, window_id):
    """Resolve a context only from explicit window_id + matching scheduled_at.

    A process start time is never used to guess a window. Exactly one STARTED
    event must exist for the requested run attempt, and exactly one run attempt
    may claim the target scheduled instant.
    """
    if not isinstance(expected_windows, list):
        raise ValueError("expected_windows must be a list")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id must be non-empty")
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
        raise ValueError("attempt must be a positive integer")
    if not isinstance(window_id, str) or not window_id.strip():
        raise ValueError("window_id must be explicit and non-empty")

    selected = [item for item in expected_windows
                if isinstance(item, dict) and item.get("window_id") == window_id]
    if len(selected) != 1:
        raise ValueError("window_id must identify exactly one expected window")
    window = selected[0]
    if set(window) != {"window_id", "scheduled_at", "expected_sources"}:
        raise ValueError("expected window structure is invalid")
    scheduled_at = _canonical_utc(window["scheduled_at"])
    sources = window["expected_sources"]
    if (not isinstance(sources, list) or not sources
            or any(not isinstance(item, str) or not item.strip() for item in sources)
            or len(set(sources)) != len(sources)):
        raise ValueError("expected_sources is invalid")

    history = verify_run_history(run_events)
    key = (run_id, attempt)
    start = history["started"].get(key)
    if start is None:
        raise ValueError("requested run attempt has no verified STARTED event")
    explicit_scheduled_at = start["payload"].get("scheduled_at")
    if explicit_scheduled_at is None:
        raise ValueError("STARTED event has no explicit scheduled_at")
    if _canonical_utc(explicit_scheduled_at) != scheduled_at:
        raise ValueError("run scheduled_at does not match the explicit window_id")

    claims = []
    for other_key, event in history["started"].items():
        other_scheduled_at = event["payload"].get("scheduled_at")
        if other_scheduled_at is not None and _canonical_utc(other_scheduled_at) == scheduled_at:
            claims.append(other_key)
    if claims != [key]:
        raise ValueError("scheduled window is claimed by zero or multiple run attempts")

    return ScheduledRunContext(
        window_id=window_id,
        scheduled_at=scheduled_at,
        run_id=run_id,
        attempt=attempt,
        expected_sources=tuple(sorted(sources)),
    )


def validate_scheduled_invocation(context, expected_windows, run_id, attempt):
    """Validate an injected schedule claim before the collector writes STARTED.

    Unlike resolve_scheduled_run_context(), this validates caller-supplied
    inputs before any journal event exists. It does not infer a schedule or
    inspect process start time; the expected-window registry is mandatory.
    """
    if not isinstance(context, ScheduledRunContext):
        raise ValueError("scheduled_context must be a ScheduledRunContext")
    if not isinstance(expected_windows, list):
        raise ValueError("expected_windows must be an explicit list")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id must be non-empty")
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
        raise ValueError("attempt must be a positive integer")
    if context.run_id != run_id or context.attempt != attempt:
        raise ValueError("scheduled context does not match this collector run attempt")

    matches = [
        item for item in expected_windows
        if isinstance(item, dict) and item.get("window_id") == context.window_id
    ]
    if len(matches) != 1:
        raise ValueError("window_id must identify exactly one expected window")
    window = matches[0]
    if set(window) != {"window_id", "scheduled_at", "expected_sources"}:
        raise ValueError("expected window structure is invalid")
    scheduled_at = _canonical_utc(window["scheduled_at"])
    sources = window["expected_sources"]
    if (
        not isinstance(sources, list)
        or not sources
        or any(not isinstance(item, str) or not item.strip() for item in sources)
        or len(set(sources)) != len(sources)
    ):
        raise ValueError("expected_sources is invalid")
    if scheduled_at != context.scheduled_at:
        raise ValueError("scheduled_at differs from the expected window")
    if tuple(sorted(sources)) != context.expected_sources:
        raise ValueError("expected_sources differ from the expected window")
    return context
