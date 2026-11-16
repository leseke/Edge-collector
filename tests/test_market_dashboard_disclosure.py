"""Offline regression guard for public TCG price provenance wording."""
from pathlib import Path
import unittest


class MarketDashboardDisclosureTests(unittest.TestCase):
    def test_price_tiles_disclose_unverified_evidence(self):
        component = (Path(__file__).resolve().parents[1] / "app/components/MarketDashboard.tsx").read_text(encoding="utf-8")
        self.assertIn("Fiabilité non vérifiée", component)
        self.assertIn("pas une vente conclue", component)
        self.assertIn("Langue non vérifiée", component)


if __name__ == "__main__":
    unittest.main()
