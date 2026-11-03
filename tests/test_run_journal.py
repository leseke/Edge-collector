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
        storage.append_run_event("run-1", "STARTED", {"sources_enabled": ["ebay"]},
                                 "2026-11-03T01:00:00Z")
        storage.append_run_event("run-1", "FINISHED", {"status": "EMPTY"},
                                 "2026-11-03T01:01:00Z")
        events = storage.list_run_events("run-1")
        self.assertEqual([x["event_type"] for x in events], ["STARTED", "FINISHED"])
        self.assertEqual(events[1]["payload"]["status"], "EMPTY")

    def test_crashed_run_remains_unfinished(self):
        storage.append_run_event("crashed", "STARTED", {},
                                 "2026-11-03T01:00:00Z")
        self.assertEqual(storage.find_unfinished_runs(),
                         [{"run_id": "crashed", "started_at": "2026-11-03T01:00:00Z"}])

    def test_finished_run_is_not_unfinished(self):
        storage.append_run_event("ok", "STARTED", {}, "2026-11-03T01:00:00Z")
        storage.append_run_event("ok", "FINISHED", {}, "2026-11-03T01:01:00Z")
        self.assertEqual(storage.find_unfinished_runs(), [])

    def test_invalid_event_type_rejected(self):
        with self.assertRaises(ValueError):
            storage.append_run_event("run-1", "UPDATE", {})

    def test_payload_must_be_object(self):
        with self.assertRaises(ValueError):
            storage.append_run_event("run-1", "STARTED", ["not", "an", "object"])


if __name__ == "__main__":
    unittest.main()
