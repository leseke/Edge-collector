import unittest
from unittest import mock

import collect
from connectors.result import completed_query, failed_query


class ScheduledCollectorSourceJournalTests(unittest.TestCase):
    def setUp(self):
        self.context = object()
        self.windows = [{"window_id": "window-a"}]
        self.journal = mock.Mock()

    @mock.patch.object(collect, "fetch_source_with_status")
    def test_scheduled_source_result_is_forwarded_to_journal(self, dispatch):
        snapshot = {"sold_price_median": 42}
        outcome = completed_query(2)
        dispatch.return_value = (snapshot, outcome)

        actual, status = collect._fetch_source(
            "ebay", {"query": "LEGO"}, "lego-check",
            mock.Mock(), self.journal, self.context, self.windows,
        )

        self.assertIs(actual, snapshot)
        self.assertIs(status, outcome)
        dispatch.assert_called_once_with("ebay", {"query": "LEGO"})
        self.journal.record_source_result.assert_called_once_with(
            self.context, self.windows, outcome, "lego-check"
        )

    @mock.patch.object(collect, "fetch_source_with_status")
    def test_scheduled_source_failure_is_journaled_without_exception_text(self, dispatch):
        outcome = failed_query(RuntimeError("private provider payload"))
        dispatch.return_value = (None, outcome)

        actual, status = collect._fetch_source(
            "ebay", {"query": "LEGO"}, "lego-check",
            mock.Mock(), self.journal, self.context, self.windows,
        )

        self.assertIsNone(actual)
        self.assertEqual(status.status, "SOURCE_FAILED")
        self.journal.record_source_result.assert_called_once()
        payload = self.journal.record_source_result.call_args.args[2]
        self.assertEqual(payload.error_type, "RuntimeError")
        self.assertNotIn("private provider payload", repr(payload))

    @mock.patch.object(collect, "fetch_source_with_status")
    def test_manual_source_keeps_legacy_fetch_and_does_not_journal(self, dispatch):
        legacy = mock.Mock(return_value={"sold_price_median": 42})

        actual, status = collect._fetch_source(
            "ebay", {"query": "LEGO"}, "lego-check", legacy
        )

        self.assertEqual(actual, {"sold_price_median": 42})
        self.assertIsNone(status)
        legacy.assert_called_once_with()
        dispatch.assert_not_called()
        self.journal.record_source_result.assert_not_called()


if __name__ == "__main__":
    unittest.main()
