"""Offline regression guard for public TCG price provenance wording."""
from pathlib import Path
import unittest


class MarketDashboardDisclosureTests(unittest.TestCase):
    def test_price_tiles_disclose_unverified_evidence(self):
        component = (Path(__file__).resolve().parents[1] / "app/components/MarketDashboard.tsx").read_text(encoding="utf-8")
        self.assertIn("Fiabilité non vérifiée", component)
        self.assertIn("pas une vente conclue", component)
        self.assertIn("Langue non vérifiée", component)
        self.assertIn('snapshot.completedSales === null ? "Non disponible" : snapshot.completedSales', component)
        self.assertIn("Transactions déclarées dans le relevé", component)
        self.assertIn("Zéro ne prouve pas une absence de transactions", component)
        self.assertNotIn("<strong>0</strong><small>Aucune transaction vérifiée", component)

    def test_unavailable_snapshot_has_unknown_sales_count(self):
        source = (Path(__file__).resolve().parents[1] / "app/lib/market-data.ts").read_text(encoding="utf-8")
        self.assertIn("completedSales: number | null", source)
        self.assertIn("completedSales: null", source)
        self.assertIn("completedSales: report.observations.filter", source)


if __name__ == "__main__":
    unittest.main()
