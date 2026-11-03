import unittest
from unittest.mock import patch

from intelligence.run_journal import SQLiteRunJournal


class SQLiteRunJournalAdapterTests(unittest.TestCase):
    def test_start_and_finish_delegate_to_storage(self):
        journal = SQLiteRunJournal()
        with patch("intelligence.run_journal.storage.append_run_event") as append:
            journal.start("run-1", {"trigger": "workflow"}, "2026-11-03T10:00:00+00:00")
            journal.finish("run-1", {"run_status": "OK"}, "2026-11-03T10:01:00+00:00")
        self.assertEqual(append.call_count, 2)
        self.assertEqual(append.call_args_list[0].args, (
            "run-1", "STARTED", {"trigger": "workflow"}, "2026-11-03T10:00:00+00:00"
        ))
        self.assertEqual(append.call_args_list[1].args, (
            "run-1", "FINISHED", {"run_status": "OK"}, "2026-11-03T10:01:00+00:00"
        ))

    def test_reads_delegate_to_storage(self):
        journal = SQLiteRunJournal()
        with patch("intelligence.run_journal.storage.list_run_events", return_value=[{"event_type": "STARTED"}]) as events, \
             patch("intelligence.run_journal.storage.find_unfinished_runs", return_value=[{"run_id": "run-2"}]) as unfinished:
            self.assertEqual(journal.events("run-1"), [{"event_type": "STARTED"}])
            self.assertEqual(journal.unfinished(), [{"run_id": "run-2"}])
        events.assert_called_once_with("run-1")
        unfinished.assert_called_once_with()

    def test_source_result_delegates_to_storage(self):
        journal = SQLiteRunJournal()
        payload = {"window_id": "w1", "source_id": "ebay", "outcome": "OBSERVED"}
        with patch("intelligence.run_journal.storage.append_run_event") as append:
            journal.source_result("run-1", payload, "2026-11-03T10:00:30+00:00")
        append.assert_called_once_with(
            "run-1", "SOURCE_RESULT", payload, "2026-11-03T10:00:30+00:00"
        )


if __name__ == "__main__":
    unittest.main()
