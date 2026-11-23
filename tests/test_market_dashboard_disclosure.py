"""Offline regression guard for public TCG price provenance wording."""
from pathlib import Path
import unittest


class MarketDashboardDisclosureTests(unittest.TestCase):
    def test_price_tiles_disclose_unverified_evidence(self):
        component = (Path(__file__).resolve().parents[1] / "app/components/MarketDashboard.tsx").read_text(encoding="utf-8")
        self.assertIn("Fiabilité non vérifiée", component)
        self.assertIn("pas une vente conclue", component)
        self.assertIn("Langue non vérifiée", component)
        self.assertIn("Nature du prix : {card.priceKind", component)
        self.assertIn("Source mise à jour : {card.sourceUpdatedAt", component)
        self.assertIn("Source déclarée : {card.source}", component)
        self.assertIn('snapshot.completedSales === null ? "Non disponible" : snapshot.completedSales', component)
        self.assertIn("Transactions déclarées dans le relevé", component)
        self.assertIn("Zéro ne prouve pas une absence de transactions", component)
        self.assertNotIn("<strong>0</strong><small>Aucune transaction vérifiée", component)

    def test_evidence_dossier_exposes_only_observation_metadata(self):
        component = (Path(__file__).resolve().parents[1] / "app/components/MarketDashboard.tsx").read_text(encoding="utf-8")
        self.assertIn('<details className="tcg-evidence-details">', component)
        self.assertIn("<summary>Consulter le dossier de preuves</summary>", component)
        self.assertIn("{card.productId}", component)
        self.assertIn("{card.snapshotId}", component)
        self.assertIn("{card.reportSha256}", component)
        self.assertIn("{card.rawSha256}", component)
        self.assertIn("pas la véracité commerciale", component)
        self.assertIn("Aucune preuve de transaction indépendante associée", component)
        self.assertIn("Absence de preuve ne signifie pas absence de ventes", component)
        self.assertIn("Préparer une enquête locale sur cette carte", component)
        self.assertIn("encodeURIComponent(card.productId)", component)

    def test_local_inquiry_prefill_requires_tcg_id_and_does_not_autorun(self):
        component = (Path(__file__).resolve().parents[1] / "app/components/LocalCompanion.tsx").read_text(encoding="utf-8")
        self.assertIn('params.get("product")', component)
        self.assertIn('params.get("name")', component)
        self.assertIn("pokemon_card_", component)
        self.assertIn("setQuestion(`Examiner les preuves disponibles", component)
        self.assertIn("Ajoute un corpus EDGE réel", component)

    def test_hashes_are_taken_from_integrity_checked_sources(self):
        source = (Path(__file__).resolve().parents[1] / "app/lib/market-data.ts").read_text(encoding="utf-8")
        self.assertIn("sha256(reportText) !== reportEntry.sha256", source)
        self.assertIn("sha256(rawText) !== item.body_sha256", source)
        self.assertIn("snapshotId: pointer.snapshot_id", source)
        self.assertIn("reportSha256: reportEntry.sha256", source)
        self.assertIn("rawSha256: item.body_sha256!", source)

    def test_corpus_export_does_not_fabricate_sales_or_sources(self):
        component = (Path(__file__).resolve().parents[1] / "app/components/TcgCorpusDownload.tsx").read_text(encoding="utf-8")
        self.assertIn('corpus_schema: "edge.corpus.v1"', component)
        self.assertIn('simulated: false', component)
        self.assertIn('tier: "unverified"', component)
        self.assertIn('measure: "other"', component)
        self.assertIn('status: "estimated"', component)
        self.assertIn('extracts: []', component)
        self.assertIn('Aucune preuve de transaction', component)
        self.assertIn("card.reportSha256", component)
        self.assertIn("card.rawSha256", component)

    def test_unavailable_snapshot_has_unknown_sales_count(self):
        source = (Path(__file__).resolve().parents[1] / "app/lib/market-data.ts").read_text(encoding="utf-8")
        self.assertIn("completedSales: number | null", source)
        self.assertIn("completedSales: null", source)
        self.assertIn("completedSales: report.observations.filter", source)

    def test_mri_does_not_display_unknown_sales_as_zero(self):
        component = (Path(__file__).resolve().parents[1] / "app/components/MarketReactionDashboard.tsx").read_text(encoding="utf-8")
        self.assertIn('snapshot.completedSales === null ? "Non disponible" : snapshot.completedSales', component)


if __name__ == "__main__":
    unittest.main()
