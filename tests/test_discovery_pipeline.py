"""Tests Discovery : campagnes, signaux, memoire, resultats a posteriori."""
import json
import os
import tempfile
import unittest
from datetime import date, datetime, timezone

from discovery.adapters import FixtureAdapter, SourceUnavailable
from discovery.campaigns import run_campaign, validate_campaign, _expansion_queries
from discovery.engine import process
from discovery.outcomes import evaluate
from discovery.pipeline import run_pipeline
from discovery.signals import analyze, quantile
from discovery.store import CandidateStore, stable_id
from edge_engine import DEFAULT_CONFIG, assert_no_private_leak
from investigation.fees import load_fee_profiles

FIX = os.path.join(os.path.dirname(__file__), "..", "discovery", "fixtures", "demo_observations.json")
AS_OF = datetime(2026, 10, 18, 9, tzinfo=timezone.utc)


class ListAdapter:
    cost_per_call = 1

    def __init__(self, data):
        self.data = data

    def search(self, q, limit=20):
        v = self.data.get(q, [])
        if isinstance(v, Exception):
            raise v
        return [dict(o) for o in v][:limit]


def obs(i, name="LEGO 10399 Test", price=100, etype="SOLD", day="2026-10-10", **kw):
    o = {"source": kw.pop("source", "s"), "source_url": f"https://example.com/{i}",
         "external_id": str(i), "observed_at": f"{day}T10:00:00Z", "name": name,
         "price_eur": price, "evidence_type": etype}
    o.update(kw)
    return o


def camp(**kw):
    c = {"id": "test-camp", "family": "price_anomaly", "queries": ["q"],
         "sources": ["a"], "max_calls": 10, "max_expansions": 0}
    c.update(kw)
    return c


class CampaignTests(unittest.TestCase):
    def test_invalid_campaign_never_runs(self):
        r = run_campaign(camp(family="magic"), {"a": ListAdapter({})})
        self.assertEqual(r["run"]["status"], "INVALID_CONFIG")
        self.assertIsNone(r["discovery"])

    def test_silent_failure_impossible(self):
        r = run_campaign(camp(), {"a": ListAdapter({"q": RuntimeError("boom " + "token" + "=abc12345")})})
        self.assertEqual(r["run"]["status"], "FAILED")
        self.assertEqual(r["run"]["calls"][0]["status"], "ERROR")
        self.assertNotIn("abc12345", json.dumps(r["run"]))

    def test_unavailable_source_is_explicit(self):
        class Off:
            def search(self, q, limit):
                raise SourceUnavailable("cle absente")
        r = run_campaign(camp(), {"a": Off()})
        self.assertEqual(r["run"]["calls"][0]["status"], "SKIPPED_UNAVAILABLE")
        self.assertEqual(r["run"]["status"], "FAILED")

    def test_missing_adapter(self):
        r = run_campaign(camp(sources=["zzz"]), {})
        self.assertEqual(r["run"]["status"], "FAILED")

    def test_partial_when_one_query_fails(self):
        r = run_campaign(camp(queries=["q", "r"]),
                         {"a": ListAdapter({"q": [obs(1)], "r": RuntimeError("x")})})
        self.assertEqual(r["run"]["status"], "PARTIAL")

    def test_empty_success_is_no_data(self):
        r = run_campaign(camp(), {"a": ListAdapter({})})
        self.assertEqual(r["run"]["status"], "NO_DATA")

    def test_budget_respected(self):
        r = run_campaign(camp(queries=["q1", "q2", "q3"], max_calls=2), {"a": ListAdapter({})})
        st = [c["status"] for c in r["run"]["calls"]]
        self.assertEqual(st.count("SKIPPED_BUDGET"), 1)
        self.assertEqual(r["run"]["n_calls_executed"], 2)

    def test_expansion_discovers_unlisted_reference(self):
        data = {"q": [obs(1, "LEGO 12345 Nouveau", etype="RETAIL_OFFER")],
                "LEGO 12345": [obs(2, "LEGO 12345 sealed")]}
        r = run_campaign(camp(max_expansions=2), {"a": ListAdapter(data)})
        self.assertIn("LEGO 12345", r["run"]["expansions"])
        self.assertEqual(r["discovery"]["summary"]["candidates"], 2)

    def test_expansion_ignores_years(self):
        q = _expansion_queries([{"name": "LEGO 2026 nouveaute"}], ["x"], set(), 3)
        self.assertNotIn("LEGO 2026", q)

    def test_timing_recorded(self):
        r = run_campaign(camp(), {"a": ListAdapter({"q": [obs(1)]})})
        self.assertIn("duration_s", r["run"]["calls"][0])


class SignalTests(unittest.TestCase):
    def cands(self, offer_price, sold_prices, offer_src="shop"):
        o = [obs("o", price=offer_price, etype="RETAIL_OFFER", source=offer_src,
                 shipping_eur=0, seller_type="PRO")]
        o += [obs(i, price=p) for i, p in enumerate(sold_prices)]
        return process(o, "c")["candidates"]

    def test_anomaly_detected_with_evidence(self):
        g = analyze(self.cands(60, [100, 100, 100]))[0]
        self.assertTrue(g["needs_investigation"])
        self.assertEqual(g["reasons"][0]["type"], "PRICE_ANOMALY")
        self.assertGreaterEqual(len(g["reasons"][0]["evidence"]), 4)

    def test_no_anomaly_below_threshold(self):
        self.assertFalse(analyze(self.cands(90, [100, 100, 100]))[0]["needs_investigation"])

    def test_listing_alone_is_not_a_sale(self):
        g = analyze(self.cands(10, []))[0]
        self.assertFalse(g["needs_investigation"])
        self.assertIn("aucune vente conclue observee : prix de revente inconnu", g["risks"])

    def test_too_few_sales_not_enough(self):
        self.assertFalse(analyze(self.cands(10, [100, 100]))[0]["needs_investigation"])

    def test_watchlist_flag(self):
        g = analyze(self.cands(60, [100] * 3), watchlist_keys=["lego:10399"])[0]
        self.assertTrue(g["in_watchlist"])

    def test_quantile(self):
        self.assertEqual(quantile([1, 2, 3, 4], 0.5), 2.5)
        self.assertIsNone(quantile([], 0.5))


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = CandidateStore(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_with(self, observations, cid="camp-1"):
        r = run_campaign(camp(id=cid), {"a": ListAdapter({"q": observations})})
        return self.store.record_campaign(r)

    def test_stable_id_and_dedup(self):
        self.assertEqual(self.run_with([obs(1)]), 1)
        self.assertEqual(self.run_with([obs(1), obs(2)], "camp-2"), 0)
        rec = self.store.get("lego:10399")
        self.assertEqual(rec["id"], stable_id("lego:10399"))
        self.assertEqual(len(rec["observations"]), 2)
        self.assertEqual(rec["campaigns"], ["camp-1", "camp-2"])
        self.assertEqual(rec["origin_campaign"], "camp-1")

    def test_initial_decision_frozen(self):
        self.run_with([obs(1)])
        self.store.record_evaluation("lego:10399", "2026-01-01T00:00:00Z", "BUY", "HIGH", 80, ["t"])
        self.store.record_evaluation("lego:10399", "2026-02-01T00:00:00Z", "WAIT", "LOW", 120, ["t2"])
        rec = self.store.get("lego:10399")
        self.assertEqual(rec["initial"]["decision"], "BUY")
        self.assertEqual(rec["initial"]["reference_price_eur"], 80)
        self.assertEqual(len(rec["evaluations"]), 2)
        with open(self.store.ledger_path) as f:
            events = [json.loads(l)["event"] for l in f]
        self.assertIn("decision_changed", events)

    def test_persistence_roundtrip(self):
        self.run_with([obs(1)])
        again = CandidateStore(self.tmp.name)
        self.assertIsNotNone(again.get("lego:10399"))

    def test_revalidation_queue(self):
        self.run_with([obs(1)])
        self.assertEqual(self.store.to_revalidate(), [])
        self.store.record_evaluation("lego:10399", "2026-01-01T00:00:00Z", "WATCH", "LOW", 80, [])
        self.assertEqual(len(self.store.to_revalidate()), 1)


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = CandidateStore(self.tmp.name)
        self.fee = {"commission_pct": 0, "payment_pct": 0, "fixed_fee_eur": 0,
                    "shipping_out_eur": 0, "packaging_eur": 0}

    def tearDown(self):
        self.tmp.cleanup()

    def seed(self, key_num, later_prices, decision="BUY"):
        name = f"LEGO {key_num} x"
        o = [obs(f"{key_num}-{i}", name=name, price=p, day="2026-04-01") for i, p in enumerate(later_prices)]
        o.append(obs(f"{key_num}-o", name=name, price=100, etype="RETAIL_OFFER", day="2026-01-01"))
        r = run_campaign(camp(id="c-" + str(key_num)), {"a": ListAdapter({"q": o})})
        self.store.record_campaign(r)
        self.store.record_evaluation(f"lego:{key_num}", "2026-01-01T00:00:00Z", decision, "MEDIUM", 100, [])

    def test_hit_loss_unresolved_and_cohort(self):
        self.seed(11111, [150, 150, 150])
        self.seed(22222, [80, 80, 80])
        self.seed(33333, [150], decision="WAIT")
        res = evaluate(self.store, date(2026, 10, 1), 90, self.fee, min_sample=20)
        outcomes = {r["product_key"]: r["outcome"] for r in res["rows"]}
        self.assertEqual(outcomes, {"lego:11111": "HIT", "lego:22222": "LOSS", "lego:33333": "UNRESOLVED"})
        self.assertEqual(res["cohort_size"], 3)
        self.assertFalse(res["conclusive"])
        self.assertIn("insuffisant", res["warning"])
        self.assertEqual(res["by_decision"]["BUY"]["hit_rate"], 0.5)

    def test_immature_decisions_excluded(self):
        self.seed(11111, [150, 150, 150])
        res = evaluate(self.store, date(2026, 2, 1), 90, self.fee)
        self.assertEqual(res["cohort_size"], 0)


class PipelineTests(unittest.TestCase):
    def test_demo_pipeline_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(os.path.dirname(FIX), "..", "demo_campaigns.json"), encoding="utf-8") as f:
                camps = json.load(f)["campaigns"]
            fa = FixtureAdapter(FIX)
            cfg = {**DEFAULT_CONFIG, "treasury": 100, "engaged": 0}
            out, invs, store = run_pipeline(camps, {"fixture": fa}, cfg, os.path.join(d, "s"),
                                            os.path.join(d, "latest.json"), os.path.join(d, "p"),
                                            as_of=AS_OF, watchlist_keys=["lego:75639"])
            self.assertTrue(out["simulated"])
            p = {x["product_key"]: x for x in out["products"]}
            self.assertFalse(p["lego:10399"]["in_watchlist"])
            self.assertEqual(p["lego:10399"]["investigation"]["decision"], "BUY")
            inv = next(i for i in invs if i["product_key"] == "lego:10399")
            # capital 100 < 259 : opportunite gardee, execution bloquee
            self.assertTrue(inv["opportunity_alert"])
            self.assertFalse(inv["funding"]["execution_ready"])
            self.assertIn("capital_insufficient", inv["funding"]["execution_blockers"])
            with open(os.path.join(d, "latest.json"), encoding="utf-8") as f:
                raw = f.read()
            assert_no_private_leak(json.loads(raw))
            self.assertNotIn("execution_ready", raw)
            self.assertEqual(out["posture"], "SIGNALS")
            self.assertIsNotNone(store.get("lego:10399")["initial"])

    def test_all_failed_is_no_conclusion(self):
        with tempfile.TemporaryDirectory() as d:
            out, _, _ = run_pipeline([camp()], {"a": ListAdapter({"q": RuntimeError("x")})},
                                     DEFAULT_CONFIG, os.path.join(d, "s"), os.path.join(d, "l.json"),
                                     os.path.join(d, "p"), as_of=AS_OF)
            self.assertEqual(out["posture"], "NO_CONCLUSION")


if __name__ == "__main__":
    unittest.main()
