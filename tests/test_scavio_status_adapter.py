import unittest
from unittest.mock import patch

from connectors.result import NO_REACTION_OBSERVED, OBSERVED, SOURCE_FAILED
from connectors.status_adapters import fetch_scavio_with_status


class ScavioStatusAdapterTests(unittest.TestCase):
    @patch("connectors.scavio.fetch_scavio_offers", return_value=None)
    def test_successful_empty_search_is_no_reaction(self, fetch):
        snapshot, outcome = fetch_scavio_with_status("test product")
        self.assertIsNone(snapshot)
        self.assertEqual(outcome.status, NO_REACTION_OBSERVED)
        self.assertTrue(outcome.query_completed)
        fetch.assert_called_once_with(
            "test product", gl="fr", hl="fr", limit=10, raise_errors=True
        )

    @patch("connectors.scavio.fetch_scavio_offers")
    def test_offers_become_observed(self, fetch):
        fetch.return_value = {"n_offers": 2, "offers": [{}, {}]}
        snapshot, outcome = fetch_scavio_with_status("test product")
        self.assertIs(snapshot, fetch.return_value)
        self.assertEqual(outcome.status, OBSERVED)
        self.assertEqual(outcome.evidence_count, 2)

    @patch("connectors.scavio.fetch_scavio_offers", side_effect=RuntimeError("private key data"))
    def test_failure_is_sanitized(self, fetch):
        snapshot, outcome = fetch_scavio_with_status("test product")
        self.assertIsNone(snapshot)
        self.assertEqual(outcome.status, SOURCE_FAILED)
        self.assertEqual(outcome.error_type, "RuntimeError")
        self.assertNotIn("private key data", repr(outcome))


if __name__ == "__main__":
    unittest.main()
