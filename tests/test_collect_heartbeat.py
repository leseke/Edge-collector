import os
import unittest
from unittest import mock

import collect


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


if __name__ == "__main__":
    unittest.main()
