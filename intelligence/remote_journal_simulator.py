"""Deterministic in-memory model of a remote append-only journal.

This is a test double, not a production backend and performs no network I/O.
It models optimistic concurrency (compare-and-swap), idempotent retries and
backend unavailability so the remote contract can be tested before provisioning.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime

STARTED_FIELDS = {"trigger", "scheduled_at"}
FINISHED_FIELDS = {
    "run_status", "sources_expected", "sources_failed",
    "collected_records", "product_price_snapshots", "retail_offer_batches",
    "error_type", "started_at", "completed_at",
}
RUN_STATUSES = {"OK", "PARTIAL", "EMPTY", "FAILED"}


class JournalConflict(RuntimeError):
    """The caller's expected journal head is stale."""


class JournalUnavailable(RuntimeError):
    """The simulated remote backend cannot be reached."""


class JournalIntegrityError(ValueError):
    """An event violates the immutable journal contract."""


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def make_event(run_id, attempt, event_type, occurred_at_utc, payload):
    """Create a stable event identity for safe retries."""
    identity = f"{run_id}\n{attempt}\n{event_type}".encode("utf-8")
    event_id = hashlib.sha256(identity).hexdigest()
    return {
        "schema_version": 1,
        "event_id": event_id,
        "run_id": run_id,
        "attempt": attempt,
        "event_type": event_type,
        "occurred_at_utc": occurred_at_utc,
        "payload": dict(payload),
    }


def _validate_event(event):
    required = {
        "schema_version", "event_id", "run_id", "attempt",
        "event_type", "occurred_at_utc", "payload",
    }
    if not isinstance(event, dict) or set(event) != required:
        raise JournalIntegrityError("structure d'événement invalide")
    if event["schema_version"] != 1:
        raise JournalIntegrityError("version de schéma non prise en charge")
    if not isinstance(event["run_id"], str) or not event["run_id"].strip():
        raise JournalIntegrityError("run_id invalide")
    if isinstance(event["attempt"], bool) or not isinstance(event["attempt"], int) or event["attempt"] < 1:
        raise JournalIntegrityError("attempt invalide")
    if event["event_type"] not in {"STARTED", "FINISHED"}:
        raise JournalIntegrityError("type d'événement invalide")
    try:
        parsed = datetime.fromisoformat(event["occurred_at_utc"].replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError):
        raise JournalIntegrityError("horodatage invalide")
    if parsed.tzinfo is None:
        raise JournalIntegrityError("timezone obligatoire")
    if not isinstance(event["payload"], dict):
        raise JournalIntegrityError("payload invalide")
    allowed = STARTED_FIELDS if event["event_type"] == "STARTED" else FINISHED_FIELDS
    if set(event["payload"]) - allowed:
        raise JournalIntegrityError("champ interdit dans le payload")
    if event["event_type"] == "FINISHED":
        if event["payload"].get("run_status") not in RUN_STATUSES:
            raise JournalIntegrityError("run_status invalide")
    expected = make_event(
        event["run_id"], event["attempt"], event["event_type"],
        event["occurred_at_utc"], event["payload"],
    )["event_id"]
    if event["event_id"] != expected:
        raise JournalIntegrityError("event_id incohérent")


class InMemoryRemoteJournal:
    """CAS journal with immutable events; state is lost when this object is lost."""

    def __init__(self):
        self._events = []
        self._head = "GENESIS"
        self.available = True

    @property
    def head(self):
        return self._head

    def read_events(self):
        if not self.available:
            raise JournalUnavailable("journal distant indisponible")
        return [json.loads(_canonical(event)) for event in self._events]

    def append_if_head(self, expected_head, event):
        if not self.available:
            raise JournalUnavailable("journal distant indisponible")
        _validate_event(event)

        key = (event["run_id"], event["attempt"], event["event_type"])
        existing = [
            item for item in self._events
            if (item["run_id"], item["attempt"], item["event_type"]) == key
        ]
        if existing:
            if _canonical(existing[0]) == _canonical(event):
                return self._head  # retry after an ambiguous successful write
            raise JournalIntegrityError("clé idempotente réutilisée avec un contenu différent")

        if expected_head != self._head:
            raise JournalConflict("tête du journal modifiée depuis la lecture")

        same_run = [
            item for item in self._events
            if item["run_id"] == event["run_id"] and item["attempt"] == event["attempt"]
        ]
        starts = sum(item["event_type"] == "STARTED" for item in same_run)
        finishes = sum(item["event_type"] == "FINISHED" for item in same_run)
        if event["event_type"] == "STARTED" and (starts or finishes):
            raise JournalIntegrityError("STARTED déjà présent pour cette tentative")
        if event["event_type"] == "FINISHED" and (starts != 1 or finishes != 0):
            raise JournalIntegrityError("FINISHED exige un STARTED unique")

        self._events.append(json.loads(_canonical(event)))
        self._head = hashlib.sha256(
            (self._head + _canonical(event)).encode("utf-8")
        ).hexdigest()
        return self._head


def append_with_retry(journal, event, max_attempts=3):
    """Append using bounded CAS retries; never suppress backend failures."""
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
        raise ValueError("max_attempts doit être un entier positif")
    for attempt in range(max_attempts):
        head = journal.head
        try:
            return journal.append_if_head(head, event)
        except JournalConflict:
            if attempt + 1 == max_attempts:
                raise
    raise JournalConflict("nombre maximal de tentatives atteint")
