import os
import tempfile
import unittest
from datetime import date

from investigation.analysis import (economic_decision, scenarios_flip,
                                    scenarios_future_classic, split_evidence)
from investigation.catalysts import evaluate_chain, match
from investigation.fees import annualize, economics, net_resale
from investigation.report import build_report, public_report, to_markdown
from searchlab.planner import plan

FEE = {"commission_pct": 10, "payment_pct": 0, "fixed_fee_eur": 1,
       "shipping_out_eur": 5, "packaging_eur": 1}


def sold(prices, day="2026-10-10"):
    return [{"evidence_type": "SOLD", "price_eur": p, "observed_at": f"{day}T00:00:00Z",
             "source": "s", "url": "https://e.com"} for p in prices]


class FeeTests(unittest.TestCase):
    def test_net_resale_hand_computed(self):
        # 100 * 0.9 - 1 - 5 - 1 = 83
        self.assertAlmostEqual(net_resale(100, FEE), 83.0)

    def test_economics(self):
        e = economics(60, 5, 100, FEE, 30)
        self.assertEqual(e["buy_total_eur"], 65)
        self.assertEqual(e["net_profit_eur"], 18.0)
        self.assertEqual(e["net_roi_pct"], 27.7)
        self.assertEqual(e["fees_eur"], 17.0)

    def test_annualize(self):
        self.assertAlmostEqual(annualize(0.1, 365), 0.1)
        self.assertIsNone(annualize(-1, 30))
        self.assertIsNone(annualize(0.1, 0))

    def test_missing_inputs(self):
        self.assertIsNone(economics(None, 0, 100, FEE, 30))
        self.assertIsNone(economics(0, 0, 100, FEE, 30))


class ScenarioDecisionTests(unittest.TestCase):
    BUY = {"price_eur": 60, "shipping_eur": 0, "total_eur": 60, "url": "https://e.com"}

    def test_flip_requires_three_sales(self):
        self.assertIsNone(scenarios_flip(sold([100, 100]), self.BUY, FEE))

    def test_flip_quantiles(self):
        s = scenarios_flip(sold([80, 100, 120, 140]), self.BUY, FEE)
        self.assertEqual(s["central"]["sale_price_eur"], 110)
        self.assertLess(s["prudent"]["net_roi_pct"], s["favorable"]["net_roi_pct"])

    def test_future_classic_needs_comparables(self):
        self.assertIsNone(scenarios_future_classic(sold([100] * 3), self.BUY, FEE, []))
        comps = [{"annual_growth_pct": g} for g in (5, 10, 15)]
        s = scenarios_future_classic(sold([100] * 3), self.BUY, FEE, comps)
        self.assertGreater(s["favorable"]["sale_price_eur"], s["prudent"]["sale_price_eur"])

    def test_decision_rules(self):
        scen = lambda p, c: {"prudent": {"net_roi_pct": p}, "central": {"net_roi_pct": c}}
        # Contrat R4 : sans scenario, NO_DATA (rien) ou WATCH (indicatif), jamais positif.
        self.assertEqual(economic_decision(None, "HIGH", 20, True)[0], "NO_DATA")
        self.assertEqual(economic_decision(None, "HIGH", 20, True, indicative_evidence=True)[0], "WATCH")
        self.assertEqual(economic_decision(scen(30, 40), "HIGH", 20, True, True)[0], "STRONG_BUY")
        self.assertEqual(economic_decision(scen(30, 40), "HIGH", 20, True, False)[0], "BUY")
        self.assertEqual(economic_decision(scen(30, 40), "HIGH", 20, False, True)[0], "WATCH")
        self.assertEqual(economic_decision(scen(-5, 25), "HIGH", 20, True, True)[0], "WATCH")
        self.assertEqual(economic_decision(scen(25, 30), "LOW", 20, True, True)[0], "WATCH")
        self.assertEqual(economic_decision(scen(0, 10), "HIGH", 20, True, True)[0], "WAIT")

    def test_split_evidence_separates_sales_and_listings(self):
        o = sold([100]) + [{"evidence_type": "ASKING_PRICE", "price_eur": 50,
                            "observed_at": "2026-10-10T00:00:00Z"}]
        s, sa, b, t = split_evidence(o, date(2026, 10, 18))
        self.assertEqual((len(s), len(b)), (1, 1))

    def test_old_sales_excluded_from_window(self):
        s, sa, _, _ = split_evidence(sold([100], "2025-01-01"), date(2026, 10, 18))
        self.assertEqual((len(s), len(sa)), (0, 1))


class CatalystTests(unittest.TestCase):
    CAT = {"id": "c", "title": "t", "date": "2027-01-01", "type": "anniversary",
           "keywords": ["pokemon"], "verified": False, "source_url": None}

    def test_match_and_unverified_never_supports(self):
        self.assertEqual(len(match("Coffret Pokémon", [self.CAT])), 1)
        ev = evaluate_chain(self.CAT, "x", sold([10] * 3), date(2026, 10, 18))
        self.assertFalse(ev["supports_thesis"])
        self.assertEqual(ev["chain"][0]["status"], "NON_VERIFIE")
        self.assertEqual(ev["chain"][1]["status"], "HYPOTHESE")

    def test_already_priced_detected(self):
        recent = sold([150] * 3, "2026-10-10")
        prior = sold([100] * 3, "2026-08-01")
        cat = dict(self.CAT, verified=True, source_url="https://e.com")
        buy = [{"evidence_type": "RETAIL_OFFER", "price_eur": 90, "observed_at": "2026-10-18T00:00:00Z"}]
        ev = evaluate_chain(cat, "x", recent + prior + buy, date(2026, 10, 18))
        self.assertAlmostEqual(ev["momentum_30d_vs_prior"], 0.5)
        self.assertFalse(ev["supports_thesis"])
        self.assertTrue(ev["competing_explanations"][0].startswith("hausse recente"))


class ReportTests(unittest.TestCase):
    def inv(self):
        s = sold([100, 105, 110])
        return {"product_key": "lego:1", "strategy": "FLIP", "sold": s, "sold_all": s,
                "buyable": [], "trend": [], "best_offer": None,
                "liquidity": {"months_of_supply": None}, "history": [], "scenarios": None,
                "confidence": {"level": "LOW", "points": 1, "why": ["x"]},
                "decision": "NO_DATA", "rationale": "r", "opportunity_alert": False,
                "funding": {"execution_ready": False, "execution_blockers": ["a"]},
                "min_net_roi_pct": 20, "catalysts": [], "comparables": [], "risks": [],
                "reasons": [], "simulated": True}

    def test_twenty_sections_and_public_strip(self):
        r = build_report(self.inv(), "n", date(2026, 10, 18))
        self.assertEqual(len(r["sections"]), 20)
        pub = public_report(r)
        self.assertNotIn("financement", pub["sections"]["20_conclusion"])
        self.assertIn("financement", r["sections"]["20_conclusion"])
        md = to_markdown(r)
        self.assertIn("SIMULÉES", md)


class SearchLabTests(unittest.TestCase):
    def test_examples_from_spec(self):
        p = plan("Produits liés aux 30 ans de Pokémon")
        self.assertEqual(p["family"], "catalyst")
        self.assertIn("Pokemon anniversaire", p["queries"])
        self.assertEqual(plan("Objets de collection prometteurs sur cinq ans")["strategy"], "FUTURE_CLASSIC")
        eol = plan("Produits dont la fabrication s'arrête prochainement")
        self.assertEqual(eol["family"], "end_of_life")
        self.assertNotIn("Produits dont la fabrication s'arrête prochainement", eol["queries"])
        self.assertEqual(plan("Consoles sous-évaluées")["family"], "price_anomaly")

    def test_set_number_triggers_sold_source(self):
        p = plan("LEGO 10316")
        self.assertIn("ebay_sold", p["sources"])
        self.assertIn("LEGO 10316", p["queries"])

    def test_deterministic_id_and_validation(self):
        self.assertEqual(plan("LEGO Pokémon")["id"], plan("LEGO Pokémon")["id"])
        for bad in ("", "  ", "x" * 300):
            with self.assertRaises(ValueError):
                plan(bad)

    def test_query_cap(self):
        self.assertLessEqual(len(plan("collection rare promo nouveau fin de serie")["queries"]), 6)

    def test_cli_end_to_end_fixtures(self):
        from searchlab.__main__ import main
        fix = os.path.join(os.path.dirname(__file__), "..", "discovery", "fixtures", "demo_observations.json")
        with tempfile.TemporaryDirectory() as d:
            main(["LEGO 10399", "--mode", "investigation", "--fixtures", fix,
                  "--as-of", "2026-10-18T09:00:00+00:00", "--out-dir", d,
                  "--store-dir", os.path.join(d, "s"), "--private-dir", os.path.join(d, "p")])
            import json
            with open(os.path.join(d, "index.json"), encoding="utf-8") as f:
                idx = json.load(f)
            self.assertEqual(idx["searches"][0]["status"], "COMPLETED")
            self.assertTrue(idx["searches"][0]["simulated"])


if __name__ == "__main__":
    unittest.main()
