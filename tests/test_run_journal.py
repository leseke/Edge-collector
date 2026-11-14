import json
import os
import tempfile
import unittest
from unittest.mock import patch

import storage


class RunJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "test.db")
        self.db_patch = patch.object(storage, "DB", self.db_path)
        self.db_patch.start()
        storage.init_db().close()

    def tearDown(self):
        self.db_patch.stop()
        self.tmp.cleanup()

    def test_events_are_appended_in_order(self):
        storage.append_run_event("run-1", "STARTED", {"trigger": "manual", "scheduled_at": None},
                                 "2026-11-03T01:00:00Z")
        storage.append_run_event("run-1", "FINISHED", {"run_status": "EMPTY"},
                                 "2026-11-03T01:01:00Z")
        events = storage.list_run_events("run-1")
        self.assertEqual([x["event_type"] for x in events], ["STARTED", "FINISHED"])
        self.assertEqual(events[1]["payload"]["run_status"], "EMPTY")

    def test_crashed_run_remains_unfinished(self):
        storage.append_run_event("crashed", "STARTED", {},
                                 "2026-11-03T01:00:00Z")
        self.assertEqual(storage.find_unfinished_runs(),
                         [{"run_id": "crashed", "started_at": "2026-11-03T01:00:00Z"}])

    def test_finished_run_is_not_unfinished(self):
        storage.append_run_event("ok", "STARTED", {}, "2026-11-03T01:00:00Z")
        storage.append_run_event("ok", "FINISHED", {}, "2026-11-03T01:01:00Z")
        self.assertEqual(storage.find_unfinished_runs(), [])

    def test_finish_requires_started_event(self):
        with self.assertRaises(ValueError):
            storage.append_run_event("orphan", "FINISHED", {})

    def test_duplicate_start_rejected(self):
        storage.append_run_event("run-1", "STARTED", {})
        with self.assertRaises(ValueError):
            storage.append_run_event("run-1", "STARTED", {})

    def test_second_finish_rejected(self):
        storage.append_run_event("run-1", "STARTED", {})
        storage.append_run_event("run-1", "FINISHED", {})
        with self.assertRaises(ValueError):
            storage.append_run_event("run-1", "FINISHED", {})

    def test_private_fields_are_rejected_from_heartbeat(self):
        with self.assertRaises(ValueError):
            storage.append_run_event("private", "STARTED", {"treasury": 300})

    def test_invalid_event_type_rejected(self):
        with self.assertRaises(ValueError):
            storage.append_run_event("run-1", "UPDATE", {})

    def test_payload_must_be_object(self):
        with self.assertRaises(ValueError):
            storage.append_run_event("run-1", "STARTED", ["not", "an", "object"])

    def test_source_result_requires_started_and_precedes_finish(self):
        result = {"window_id": "window-1", "source_id": "ebay", "outcome": "OBSERVED"}
        with self.assertRaises(ValueError):
            storage.append_run_event("run-source", "SOURCE_RESULT", result)
        storage.append_run_event("run-source", "STARTED", {})
        storage.append_run_event("run-source", "SOURCE_RESULT", result)
        storage.append_run_event("run-source", "FINISHED", {"run_status": "OK"})
        with self.assertRaises(ValueError):
            storage.append_run_event("run-source", "SOURCE_RESULT", {
                "window_id": "window-1", "source_id": "reddit",
                "outcome": "NO_REACTION_OBSERVED",
            })

    def test_multiple_source_results_are_preserved(self):
        storage.append_run_event("run-multi", "STARTED", {})
        storage.append_run_event("run-multi", "SOURCE_RESULT", {
            "window_id": "window-1", "source_id": "ebay", "outcome": "OBSERVED",
        })
        storage.append_run_event("run-multi", "SOURCE_RESULT", {
            "window_id": "window-1", "source_id": "reddit",
            "outcome": "NO_REACTION_OBSERVED",
        })
        events = storage.list_run_events("run-multi")
        self.assertEqual([event["event_type"] for event in events],
                         ["STARTED", "SOURCE_RESULT", "SOURCE_RESULT"])
        self.assertEqual(events[2]["payload"]["source_id"], "reddit")

    def test_identical_source_result_retry_is_idempotent(self):
        storage.append_run_event("run-retry", "STARTED", {})
        result = {"window_id": "window-1", "source_id": "ebay", "outcome": "OBSERVED"}
        storage.append_run_event("run-retry", "SOURCE_RESULT", result)
        storage.append_run_event("run-retry", "SOURCE_RESULT", result)
        self.assertEqual(len(storage.list_run_events("run-retry")), 2)

    def test_changed_source_result_retry_is_rejected(self):
        storage.append_run_event("run-change", "STARTED", {})
        storage.append_run_event("run-change", "SOURCE_RESULT", {
            "window_id": "window-1", "source_id": "ebay", "outcome": "OBSERVED",
        })
        with self.assertRaises(ValueError):
            storage.append_run_event("run-change", "SOURCE_RESULT", {
                "window_id": "window-1", "source_id": "ebay", "outcome": "SOURCE_FAILED",
            })

    def test_source_result_rejects_unknown_outcome_and_private_fields(self):
        storage.append_run_event("run-safe", "STARTED", {})
        with self.assertRaises(ValueError):
            storage.append_run_event("run-safe", "SOURCE_RESULT", {
                "window_id": "window-1", "source_id": "ebay", "outcome": "EMPTY",
            })
        with self.assertRaises(ValueError):
            storage.append_run_event("run-safe", "SOURCE_RESULT", {
                "window_id": "window-1", "source_id": "ebay",
                "outcome": "OBSERVED", "capital": 300,
            })

    def test_source_result_requires_nonempty_identity(self):
        storage.append_run_event("run-invalid", "STARTED", {})
        with self.assertRaises(ValueError):
            storage.append_run_event("run-invalid", "SOURCE_RESULT", {
                "window_id": "", "source_id": "ebay", "outcome": "OBSERVED",
            })


if __name__ == "__main__":
    unittest.main()
