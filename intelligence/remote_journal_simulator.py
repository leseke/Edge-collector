"""Deterministic in-memory model of a remote append-only journal.

The simulator supports execution lifecycle events and minimal source outcomes.
It performs no network I/O and is not a production persistence backend.
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
SOURCE_RESULT_FIELDS = {"window_id", "source_id", "outcome"}
RUN_STATUSES = {"OK", "PARTIAL", "EMPTY", "FAILED"}
SOURCE_OUTCOMES = {"OBSERVED", "NO_REACTION_OBSERVED", "SOURCE_FAILED"}


class JournalConflict(RuntimeError):
    """The caller's expected journal head is stale."""


class JournalUnavailable(RuntimeError):
    """The simulated remote backend cannot be reached."""


class JournalIntegrityError(ValueError):
    """An event violates the immutable journal contract."""


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _event_identity(run_id, attempt, event_type, payload):
    identity = [run_id, attempt, event_type]
    if event_type == "SOURCE_RESULT":
        identity.extend([payload.get("window_id"), payload.get("source_id")])
    return hashlib.sha256(_canonical(identity).encode("utf-8")).hexdigest()


def make_event(run_id, attempt, event_type, occurred_at_utc, payload):
    """Create a stable event identity for safe retries."""
    return {
        "schema_version": 1,
        "event_id": _event_identity(run_id, attempt, event_type, payload),
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
    if event["event_type"] not in {"STARTED", "FINISHED", "SOURCE_RESULT"}:
        raise JournalIntegrityError("type d'événement invalide")
    try:
        parsed = datetime.fromisoformat(event["occurred_at_utc"].replace("Z", "+00:00"))
    except (TypeError, ValueError, AttributeError):
        raise JournalIntegrityError("horodatage invalide")
    if parsed.tzinfo is None:
        raise JournalIntegrityError("timezone obligatoire")
    if not isinstance(event["payload"], dict):
        raise JournalIntegrityError("payload invalide")
    allowed = {
        "STARTED": STARTED_FIELDS,
        "FINISHED": FINISHED_FIELDS,
        "SOURCE_RESULT": SOURCE_RESULT_FIELDS,
    }[event["event_type"]]
    if set(event["payload"]) - allowed:
        raise JournalIntegrityError("champ interdit dans le payload")
    if event["event_type"] == "FINISHED":
        if event["payload"].get("run_status") not in RUN_STATUSES:
            raise JournalIntegrityError("run_status invalide")
    if event["event_type"] == "SOURCE_RESULT":
        payload = event["payload"]
        if not isinstance(payload.get("window_id"), str) or not payload["window_id"].strip():
            raise JournalIntegrityError("window_id invalide")
        if not isinstance(payload.get("source_id"), str) or not payload["source_id"].strip():
            raise JournalIntegrityError("source_id invalide")
        if payload.get("outcome") not in SOURCE_OUTCOMES:
            raise JournalIntegrityError("outcome source invalide")
    expected = _event_identity(
        event["run_id"], event["attempt"], event["event_type"], event["payload"]
    )
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

        payload = event["payload"]
        key = (event["run_id"], event["attempt"], event["event_type"])
        if event["event_type"] == "SOURCE_RESULT":
            key += (payload["window_id"], payload["source_id"])
        existing = []
        for item in self._events:
            item_key = (item["run_id"], item["attempt"], item["event_type"])
            if item["event_type"] == "SOURCE_RESULT":
                item_key += (item["payload"]["window_id"], item["payload"]["source_id"])
            if item_key == key:
                existing.append(item)
        if existing:
            if _canonical(existing[0]) == _canonical(event):
                return self._head
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
        if event["event_type"] == "SOURCE_RESULT" and (starts != 1 or finishes != 0):
            raise JournalIntegrityError("SOURCE_RESULT exige un STARTED et précède FINISHED")

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
