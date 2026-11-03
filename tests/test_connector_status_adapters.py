import unittest
from unittest.mock import patch

from connectors.result import OBSERVED, SOURCE_FAILED, UNKNOWN
from connectors import ebay, cardmarket


class EbayStatusAdapterTests(unittest.TestCase):
    @patch("connectors.ebay.fetch_sold")
    def test_snapshot_becomes_observed(self, fetch):
        fetch.return_value = {"_n_filtered": 4, "sold_price_median": 12.5}
        snapshot, outcome = ebay.fetch_sold_with_status("test query")
        self.assertIs(snapshot, fetch.return_value)
        self.assertEqual(outcome.status, OBSERVED)
        self.assertEqual(outcome.evidence_count, 4)

    @patch("connectors.ebay.fetch_sold", return_value=None)
    def test_legacy_none_stays_unknown(self, fetch):
        snapshot, outcome = ebay.fetch_sold_with_status("test query")
        self.assertIsNone(snapshot)
        self.assertEqual(outcome.status, UNKNOWN)

    @patch("connectors.ebay.fetch_sold", side_effect=TimeoutError("private response"))
    def test_exception_is_sanitized(self, fetch):
        snapshot, outcome = ebay.fetch_sold_with_status("test query")
        self.assertIsNone(snapshot)
        self.assertEqual(outcome.status, SOURCE_FAILED)
        self.assertEqual(outcome.error_type, "TimeoutError")
        self.assertNotIn("private response", repr(outcome))


class CardmarketStatusAdapterTests(unittest.TestCase):
    @patch("connectors.cardmarket.fetch_cardmarket")
    def test_snapshot_becomes_observed(self, fetch):
        fetch.return_value = {"_n_matched": 3, "sold_price_median": 45}
        snapshot, outcome = cardmarket.fetch_cardmarket_with_status(
            "pokemon", "sealed box"
        )
        self.assertIs(snapshot, fetch.return_value)
        self.assertEqual(outcome.status, OBSERVED)
        self.assertEqual(outcome.evidence_count, 3)

    @patch("connectors.cardmarket.fetch_cardmarket", return_value=None)
    def test_legacy_none_stays_unknown(self, fetch):
        snapshot, outcome = cardmarket.fetch_cardmarket_with_status(
            "pokemon", "sealed box"
        )
        self.assertIsNone(snapshot)
        self.assertEqual(outcome.status, UNKNOWN)

    @patch("connectors.cardmarket.fetch_cardmarket", side_effect=ValueError("sensitive payload"))
    def test_exception_is_sanitized(self, fetch):
        snapshot, outcome = cardmarket.fetch_cardmarket_with_status(
            "pokemon", "sealed box"
        )
        self.assertIsNone(snapshot)
        self.assertEqual(outcome.status, SOURCE_FAILED)
        self.assertEqual(outcome.error_type, "ValueError")
        self.assertNotIn("sensitive payload", repr(outcome))


if __name__ == "__main__":
    unittest.main()
