import json
import os
import tempfile
import unittest

from discovery.campaigns import _expansion_queries, load_campaigns
from discovery.pipeline import _is_tcg_candidate


ROOT = os.path.dirname(os.path.dirname(__file__))


class ActiveCampaignScopeTests(unittest.TestCase):
    def test_production_registry_is_tcg_only(self):
        campaigns = load_campaigns(os.path.join(ROOT, "discovery", "campaigns.json"))
        self.assertTrue(campaigns)
        self.assertTrue(all(c.get("scope") == "TCG_ONLY" for c in campaigns))
        static = [c for c in campaigns if c.get("queries")]
        self.assertTrue(all(
            any(game in query.lower() for query in c["queries"])
            for c in static for game in ("pokemon", "one piece", "riftbound", "lorcana")
        ))

    def test_active_legacy_campaign_is_rejected(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as f:
            json.dump({"scope_policy": "TCG_ONLY", "campaigns": [{
                "id": "lego-retail", "enabled": True, "scope": "TCG_ONLY",
                "queries": ["LEGO promo"], "sources": ["scavio_retail_fr"]
            }]}, f)
            path = f.name
        try:
            with self.assertRaisesRegex(ValueError, "hors perimetre TCG"):
                load_campaigns(path)
        finally:
            os.unlink(path)

    def test_revalidation_fails_closed_for_legacy_records(self):
        self.assertTrue(_is_tcg_candidate({
            "product_key": "name:one-piece-op01-display",
            "name": "One Piece OP-01 Booster Display"
        }))
        self.assertTrue(_is_tcg_candidate({
            "product_key": "pokemon:sv151",
            "name": "Pokemon 151 display"
        }))
        self.assertFalse(_is_tcg_candidate({
            "product_key": "lego:75639",
            "name": "LEGO One Piece Going Merry"
        }))
        self.assertFalse(_is_tcg_candidate({
            "product_key": "name:unknown-product",
            "name": "Unknown collectible"
        }))

    def test_expansion_is_not_hardcoded_to_lego(self):
        observations = [
            {"name": "Pokemon 151 Booster Display"},
            {"name": "Pokemon 151 Elite Trainer Box"},
            {"name": "Pokemon 151 Collection"},
        ]
        queries = _expansion_queries(observations, ["Pokemon coffret"], set(), 3)
        self.assertIn("Pokemon coffret 151", queries)
        self.assertFalse(any(q.startswith("LEGO ") for q in queries))


if __name__ == "__main__":
    unittest.main()
