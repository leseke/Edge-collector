import unittest
from unittest.mock import patch

from connectors.result import OBSERVED, NO_REACTION_OBSERVED, UNKNOWN, SOURCE_FAILED
from connectors.status_adapters import fetch_source_with_status


class SourceStatusDispatchTests(unittest.TestCase):
    @patch("connectors.ebay.fetch_sold_with_status")
    def test_ebay_dispatch_preserves_snapshot_and_outcome(self, fetch):
        snapshot = {"sold_price_median": 42}
        outcome = __import__("connectors.result", fromlist=["completed_query"]).completed_query(2)
        fetch.return_value = (snapshot, outcome)
        actual, status = fetch_source_with_status("ebay", {
            "query": "LEGO 77073", "must_all": ["77073"], "must_any": ["lego"],
        })
        self.assertIs(actual, snapshot)
        self.assertIs(status, outcome)
        fetch.assert_called_once_with(
            "LEGO 77073", must_all=["77073"], must_any=["lego"], count=100
        )

    @patch("connectors.cardmarket.fetch_cardmarket_with_status")
    def test_cardmarket_dispatch_uses_sealed_default_and_filters(self, fetch):
        from connectors.result import completed_query
        snapshot = {"sold_price_median": 100}
        outcome = completed_query(1)
        fetch.return_value = (snapshot, outcome)
        actual, status = fetch_source_with_status("cardmarket", {
            "game": "lorcana", "search_query": "Hyperia",
            "must_all": ["hyperia"], "must_not": ["case"],
        })
        self.assertIs(actual, snapshot)
        self.assertIs(status, outcome)
        fetch.assert_called_once_with(
            game="lorcana", search_query="Hyperia", product_type="sealed",
            must_all=["hyperia"], must_any=None, must_not=["case"],
        )

    @patch("connectors.trends_spy.fetch_trends_spy_with_status")
    def test_trends_dispatch(self, fetch):
        from connectors.result import completed_query
        fetch.return_value = ({"trend_acceleration": 1.3}, completed_query(1))
        snapshot, outcome = fetch_source_with_status("trends", {"keyword": "Lorcana"})
        self.assertEqual(snapshot["trend_acceleration"], 1.3)
        self.assertEqual(outcome.status, OBSERVED)
        fetch.assert_called_once_with("Lorcana")

    @patch("connectors.reddit.fetch_reddit_with_status")
    def test_reddit_dispatch(self, fetch):
        from connectors.result import completed_query
        fetch.return_value = ({"reddit_total": 0}, completed_query(3))
        snapshot, outcome = fetch_source_with_status(
            "reddit", {"subreddit": "lego", "query": "Mew"}
        )
        self.assertEqual(snapshot["reddit_total"], 0)
        self.assertEqual(outcome.status, OBSERVED)
        fetch.assert_called_once_with("lego", "Mew", limit=25)

    @patch("connectors.status_adapters.fetch_scavio_with_status")
    def test_scavio_dispatch(self, fetch):
        from connectors.result import completed_query
        fetch.return_value = (None, completed_query(0))
        snapshot, outcome = fetch_source_with_status("scavio", {"query": "LEGO"})
        self.assertIsNone(snapshot)
        self.assertEqual(outcome.status, NO_REACTION_OBSERVED)
        fetch.assert_called_once_with("LEGO", gl="fr", hl="fr", limit=10)

    def test_unknown_provider_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported"):
            fetch_source_with_status("unknown", {"query": "x"})

    def test_missing_required_field_is_not_silently_reclassified(self):
        with self.assertRaises(KeyError):
            fetch_source_with_status("ebay", {})

    @patch("connectors.ebay.fetch_sold_with_status", return_value=(None, UNKNOWN))
    def test_ambiguous_legacy_none_remains_unknown(self, fetch):
        snapshot, outcome = fetch_source_with_status("ebay", {"query": "LEGO"})
        self.assertIsNone(snapshot)
        self.assertEqual(outcome.status, UNKNOWN)

    @patch("connectors.ebay.fetch_sold_with_status", return_value=(None, SOURCE_FAILED))
    def test_source_failure_is_preserved(self, fetch):
        snapshot, outcome = fetch_source_with_status("ebay", {"query": "LEGO"})
        self.assertIsNone(snapshot)
        self.assertEqual(outcome.status, SOURCE_FAILED)


if __name__ == "__main__":
    unittest.main()
