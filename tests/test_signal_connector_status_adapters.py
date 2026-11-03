import unittest
from unittest.mock import patch

from connectors.result import OBSERVED, UNKNOWN, SOURCE_FAILED
from connectors import trends_spy, reddit


class TrendsStatusAdapterTests(unittest.TestCase):
    @patch("connectors.trends_spy.fetch_trends_spy")
    def test_snapshot_becomes_observed(self, fetch):
        fetch.return_value = {"trend_acceleration": 1.4}
        snapshot, outcome = trends_spy.fetch_trends_spy_with_status("test")
        self.assertIs(snapshot, fetch.return_value)
        self.assertEqual(outcome.status, OBSERVED)
        self.assertEqual(outcome.evidence_count, 1)

    @patch("connectors.trends_spy.fetch_trends_spy", return_value=None)
    def test_ambiguous_none_stays_unknown(self, fetch):
        snapshot, outcome = trends_spy.fetch_trends_spy_with_status("test")
        self.assertIsNone(snapshot)
        self.assertEqual(outcome.status, UNKNOWN)

    @patch("connectors.trends_spy.fetch_trends_spy", side_effect=TimeoutError("private"))
    def test_uncaught_exception_is_sanitized(self, fetch):
        snapshot, outcome = trends_spy.fetch_trends_spy_with_status("test")
        self.assertIsNone(snapshot)
        self.assertEqual(outcome.status, SOURCE_FAILED)
        self.assertNotIn("private", repr(outcome))


class RedditStatusAdapterTests(unittest.TestCase):
    @patch("connectors.reddit.fetch_reddit")
    def test_snapshot_becomes_observed(self, fetch):
        fetch.return_value = {"reddit_total": 5}
        snapshot, outcome = reddit.fetch_reddit_with_status("lego", "set")
        self.assertIs(snapshot, fetch.return_value)
        self.assertEqual(outcome.status, OBSERVED)
        self.assertEqual(outcome.evidence_count, 5)

    @patch("connectors.reddit.fetch_reddit", return_value=None)
    def test_ambiguous_none_stays_unknown(self, fetch):
        snapshot, outcome = reddit.fetch_reddit_with_status("lego", "set")
        self.assertIsNone(snapshot)
        self.assertEqual(outcome.status, UNKNOWN)

    @patch("connectors.reddit.fetch_reddit", side_effect=ConnectionError("private"))
    def test_uncaught_exception_is_sanitized(self, fetch):
        snapshot, outcome = reddit.fetch_reddit_with_status("lego", "set")
        self.assertIsNone(snapshot)
        self.assertEqual(outcome.status, SOURCE_FAILED)
        self.assertNotIn("private", repr(outcome))


if __name__ == "__main__":
    unittest.main()
