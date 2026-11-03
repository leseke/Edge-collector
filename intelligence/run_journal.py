"""Backend-neutral contract for EDGE's execution journal.

The remote backend is intentionally not implemented here. SQLite remains the
only active adapter until a private durable store is provisioned and tested.
"""
from typing import Any, Protocol

import storage


class RunJournal(Protocol):
    def start(self, run_id: str, payload: dict[str, Any], occurred_at: str | None = None) -> None:
        """Append one STARTED event."""
        ...

    def finish(self, run_id: str, payload: dict[str, Any], occurred_at: str | None = None) -> None:
        """Append one FINISHED event."""
        ...

    def events(self, run_id: str) -> list[dict[str, Any]]:
        """Return events in append order."""
        ...

    def unfinished(self) -> list[dict[str, Any]]:
        """Return runs with STARTED and no FINISHED event."""
        ...


class SQLiteRunJournal:
    """Local runner adapter; not durable across ephemeral CI runners."""

    def start(self, run_id: str, payload: dict[str, Any], occurred_at: str | None = None) -> None:
        storage.append_run_event(run_id, "STARTED", payload, occurred_at)

    def finish(self, run_id: str, payload: dict[str, Any], occurred_at: str | None = None) -> None:
        storage.append_run_event(run_id, "FINISHED", payload, occurred_at)

    def events(self, run_id: str) -> list[dict[str, Any]]:
        return storage.list_run_events(run_id)

    def unfinished(self) -> list[dict[str, Any]]:
        return storage.find_unfinished_runs()
