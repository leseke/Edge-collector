import unittest

from intelligence.remote_journal_simulator import (
    InMemoryRemoteJournal, JournalConflict, JournalIntegrityError,
    JournalUnavailable, append_with_retry, make_event,
)


T0 = "2026-11-03T01:00:00Z"
T1 = "2026-11-03T01:01:00Z"


def started(run_id, attempt=1):
    return make_event(run_id, attempt, "STARTED", T0, {"trigger": "schedule", "scheduled_at": T0})


def finished(run_id, attempt=1):
    return make_event(run_id, attempt, "FINISHED", T1, {
        "run_status": "OK", "sources_expected": ["scavio"],
        "sources_failed": [], "collected_records": 1,
        "product_price_snapshots": 1, "retail_offer_batches": 0,
        "started_at": T0, "completed_at": T1,
    })


class RemoteJournalSimulatorTests(unittest.TestCase):
    def test_append_and_restore_from_event_stream(self):
        journal = InMemoryRemoteJournal()
        append_with_retry(journal, started("run-a"))
        append_with_retry(journal, finished("run-a"))
        restored = journal.read_events()
        self.assertEqual([e["event_type"] for e in restored], ["STARTED", "FINISHED"])
        self.assertEqual(restored[0]["run_id"], "run-a")

    def test_retry_after_ambiguous_success_is_idempotent(self):
        journal = InMemoryRemoteJournal()
        event = started("run-a")
        stale_head = journal.head
        journal.append_if_head(stale_head, event)  # server committed; client lost response
        current_head = journal.head
        self.assertEqual(journal.append_if_head(stale_head, event), current_head)
        self.assertEqual(len(journal.read_events()), 1)

    def test_two_writers_cannot_overwrite_each_other(self):
        journal = InMemoryRemoteJournal()
        shared_head = journal.head
        first = started("run-a")
        second = started("run-b")
        journal.append_if_head(shared_head, first)
        with self.assertRaises(JournalConflict):
            journal.append_if_head(shared_head, second)
        # The second writer re-reads and retries; both events survive.
        append_with_retry(journal, second)
        self.assertEqual({e["run_id"] for e in journal.read_events()}, {"run-a", "run-b"})

    def test_duplicate_key_with_changed_payload_is_rejected(self):
        journal = InMemoryRemoteJournal()
        journal.append_if_head(journal.head, started("run-a"))
        changed = make_event("run-a", 1, "STARTED", T0, {"trigger": "manual"})
        with self.assertRaises(JournalIntegrityError):
            journal.append_if_head(journal.head, changed)

    def test_finish_without_start_is_rejected(self):
        journal = InMemoryRemoteJournal()
        with self.assertRaises(JournalIntegrityError):
            journal.append_if_head(journal.head, finished("run-a"))

    def test_second_finish_is_rejected(self):
        journal = InMemoryRemoteJournal()
        append_with_retry(journal, started("run-a"))
        append_with_retry(journal, finished("run-a"))
        with self.assertRaises(JournalIntegrityError):
            journal.append_if_head(journal.head, finished("run-a", attempt=2))

    def test_private_fields_are_rejected(self):
        journal = InMemoryRemoteJournal()
        event = make_event("run-a", 1, "STARTED", T0, {
            "trigger": "schedule", "capital": 300,
        })
        with self.assertRaises(JournalIntegrityError):
            journal.append_if_head(journal.head, event)

    def test_unavailable_backend_is_not_silently_accepted(self):
        journal = InMemoryRemoteJournal()
        journal.available = False
        with self.assertRaises(JournalUnavailable):
            append_with_retry(journal, started("run-a"))

    def test_retry_limit_is_bounded(self):
        journal = InMemoryRemoteJournal()
        with self.assertRaises(ValueError):
            append_with_retry(journal, started("run-a"), max_attempts=0)


if __name__ == "__main__":
    unittest.main()
