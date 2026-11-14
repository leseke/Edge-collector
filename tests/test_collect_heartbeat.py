import os
import unittest
from unittest import mock

import collect
from intelligence.scheduled_run_context import ScheduledRunContext


class CollectorHeartbeatTests(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {}, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()

    @mock.patch.object(collect, "init_db")
    @mock.patch.object(collect, "append_run_event")
    @mock.patch.object(collect, "_run_once", return_value={
        "run_status": "OK",
        "sources_expected": ["ebay"],
        "sources_failed": [],
        "collected_records": 1,
        "product_price_snapshots": 1,
        "retail_offer_batches": 0,
    })
    def test_run_records_started_and_finished(self, run_once, append_event, init_db):
        result = collect.run()
        self.assertEqual(result["run_status"], "OK")
        self.assertEqual([call.args[1] for call in append_event.call_args_list],
                         ["STARTED", "FINISHED"])
        self.assertIsNone(append_event.call_args_list[0].args[2]["scheduled_at"])
        self.assertEqual(append_event.call_args_list[1].args[2]["run_status"], "OK")
        init_db.assert_called_once()

    @mock.patch.object(collect, "init_db")
    @mock.patch.object(collect, "append_run_event")
    @mock.patch.object(collect, "_run_once", side_effect=KeyboardInterrupt())
    def test_keyboard_interrupt_is_not_recorded_as_empty(self, run_once, append_event, init_db):
        with self.assertRaises(KeyboardInterrupt):
            collect.run()
        payload = append_event.call_args_list[1].args[2]
        self.assertEqual(payload["run_status"], "FAILED")
        self.assertEqual(payload["error_type"], "KeyboardInterrupt")

    @mock.patch.object(collect, "init_db")
    @mock.patch.object(collect, "append_run_event")
    @mock.patch.object(collect, "_run_once", side_effect=RuntimeError("sensitive raw error"))
    def test_run_records_failed_finish_without_raw_exception(self, run_once, append_event, init_db):
        with self.assertRaisesRegex(RuntimeError, "sensitive raw error"):
            collect.run()
        self.assertEqual([call.args[1] for call in append_event.call_args_list],
                         ["STARTED", "FINISHED"])
        payload = append_event.call_args_list[1].args[2]
        self.assertEqual(payload["run_status"], "FAILED")
        self.assertEqual(payload["error_type"], "RuntimeError")
        self.assertNotIn("sensitive raw error", str(payload))


    @mock.patch.object(collect, "init_db")
    @mock.patch.object(collect, "append_run_event")
    @mock.patch.object(collect, "SQLiteContinuityJournal")
    @mock.patch.object(collect, "_run_once", return_value={
        "run_status": "OK",
        "sources_expected": ["ebay:item-a"],
        "sources_failed": [],
        "collected_records": 1,
        "product_price_snapshots": 1,
        "retail_offer_batches": 0,
    })
    def test_explicit_scheduled_context_is_written_without_inference(
        self, run_once, journal_class, append_event, init_db
    ):
        os.environ["GITHUB_RUN_ID"] = "123"
        os.environ["GITHUB_RUN_ATTEMPT"] = "2"
        window = {
            "window_id": "hourly:20261103T010000Z",
            "scheduled_at": "2026-11-03T01:00:00Z",
            "expected_sources": ["ebay:item-a"],
        }
        context = ScheduledRunContext(
            window_id=window["window_id"],
            scheduled_at=window["scheduled_at"],
            run_id="edge-123-attempt-2",
            attempt=2,
            expected_sources=("ebay:item-a",),
        )

        result = collect.run(scheduled_context=context, expected_windows=[window])

        self.assertEqual(result["run_status"], "OK")
        journal_class.return_value.start.assert_called_once_with(
            context, [window], occurred_at=mock.ANY
        )
        journal_class.return_value.finish.assert_called_once()
        append_event.assert_not_called()
        init_db.assert_called_once()

    @mock.patch.object(collect, "init_db")
    @mock.patch.object(collect, "append_run_event")
    def test_invalid_scheduled_context_is_rejected_before_any_journal_write(
        self, append_event, init_db
    ):
        os.environ["GITHUB_RUN_ID"] = "123"
        os.environ["GITHUB_RUN_ATTEMPT"] = "1"
        window = {
            "window_id": "hourly:20261103T010000Z",
            "scheduled_at": "2026-11-03T01:00:00Z",
            "expected_sources": ["ebay:item-a"],
        }
        context = ScheduledRunContext(
            window_id=window["window_id"],
            scheduled_at=window["scheduled_at"],
            run_id="some-other-run",
            attempt=1,
            expected_sources=("ebay:item-a",),
        )

        with self.assertRaisesRegex(ValueError, "run attempt"):
            collect.run(scheduled_context=context, expected_windows=[window])
        init_db.assert_not_called()
        append_event.assert_not_called()

    def test_expected_windows_without_context_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "requires an explicit"):
            collect.run(expected_windows=[])


if __name__ == "__main__":
    unittest.main()
