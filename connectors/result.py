"""Minimal, privacy-safe outcome contract for one source check.

This module deliberately does not infer completion from legacy connector values.
Callers must explicitly attest that a query completed before a zero-result
outcome can become NO_REACTION_OBSERVED.
"""
from dataclasses import dataclass
from typing import Optional


OBSERVED = "OBSERVED"
NO_REACTION_OBSERVED = "NO_REACTION_OBSERVED"
SOURCE_FAILED = "SOURCE_FAILED"
NOT_SCHEDULED = "NOT_SCHEDULED"
UNKNOWN = "UNKNOWN"

_ALLOWED_STATUSES = {
    OBSERVED, NO_REACTION_OBSERVED, SOURCE_FAILED, NOT_SCHEDULED, UNKNOWN,
}


@dataclass(frozen=True)
class ConnectorResult:
    """Sanitized outcome; never stores provider payloads or exception messages."""

    status: str
    query_completed: bool
    evidence_count: Optional[int] = None
    error_type: Optional[str] = None

    def __post_init__(self):
        if self.status not in _ALLOWED_STATUSES:
            raise ValueError("invalid connector result status")
        if not isinstance(self.query_completed, bool):
            raise ValueError("query_completed must be boolean")
        if self.evidence_count is not None:
            if isinstance(self.evidence_count, bool) or not isinstance(self.evidence_count, int):
                raise ValueError("evidence_count must be an integer or None")
            if self.evidence_count < 0:
                raise ValueError("evidence_count must be non-negative")
        if self.error_type is not None:
            if not isinstance(self.error_type, str) or not self.error_type.strip():
                raise ValueError("error_type must be a non-empty class name or None")
            if any(ch in self.error_type for ch in "\\r\\n"):
                raise ValueError("error_type must be a single-line class name")

        if self.status == OBSERVED:
            if not self.query_completed or not self.evidence_count:
                raise ValueError("OBSERVED requires a completed query and evidence")
            if self.error_type is not None:
                raise ValueError("OBSERVED cannot include an error")
        elif self.status == NO_REACTION_OBSERVED:
            if not self.query_completed or self.evidence_count != 0:
                raise ValueError("NO_REACTION_OBSERVED requires a completed empty query")
            if self.error_type is not None:
                raise ValueError("NO_REACTION_OBSERVED cannot include an error")
        elif self.status == SOURCE_FAILED:
            if self.query_completed or self.error_type is None:
                raise ValueError("SOURCE_FAILED requires an error before query completion")
        elif self.status == NOT_SCHEDULED:
            if self.query_completed or self.evidence_count is not None or self.error_type is not None:
                raise ValueError("NOT_SCHEDULED cannot contain execution results")
        elif self.status == UNKNOWN:
            if self.query_completed or self.evidence_count is not None or self.error_type is not None:
                raise ValueError("UNKNOWN cannot claim execution evidence")

    def to_event_payload(self, window_id, source_id):
        """Return only the strict journal SOURCE_RESULT allowlist."""
        if self.status not in {OBSERVED, NO_REACTION_OBSERVED, SOURCE_FAILED}:
            raise ValueError("non-execution outcomes must not be journaled as SOURCE_RESULT")
        if not isinstance(window_id, str) or not window_id.strip():
            raise ValueError("window_id must be non-empty")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("source_id must be non-empty")
        return {
            "window_id": window_id,
            "source_id": source_id,
            "outcome": self.status,
        }


def completed_query(evidence_count):
    """Build an outcome only after the adapter has positively confirmed completion."""
    if isinstance(evidence_count, bool) or not isinstance(evidence_count, int):
        raise ValueError("evidence_count must be an integer")
    if evidence_count < 0:
        raise ValueError("evidence_count must be non-negative")
    if evidence_count == 0:
        return ConnectorResult(NO_REACTION_OBSERVED, True, 0)
    return ConnectorResult(OBSERVED, True, evidence_count)


def failed_query(error):
    """Record only the exception class, never its message or attached data."""
    if error is None:
        raise ValueError("error is required")
    error_type = type(error).__name__
    return ConnectorResult(SOURCE_FAILED, False, None, error_type)


def not_scheduled():
    return ConnectorResult(NOT_SCHEDULED, False)


def unknown():
    return ConnectorResult(UNKNOWN, False)
