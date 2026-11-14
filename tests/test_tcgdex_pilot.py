"""Pilote TCGdex : schema documente, variantes, fraicheur, enregistrement,
cache, sonde de bout en bout, absence de decision positive."""
import glob
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone

from discovery.adapters_official import HttpError, TcgdexAdapter, validate_card_pricing
from discovery.fixture_http import FixtureTransport
from discovery.recording_http import RecordingCachingTransport

ROOT = os.path.join(os.path.dirname(__file__), "..")
DOC = os.path.join(ROOT, "tests", "fixtures", "tcgdex_doc_example.json")
LIVE = os.path.join(ROOT, "tests", "fixtures", "tcgdex_live")
NOW = datetime(2026, 10, 18, 9, tzinfo=timezone.utc)


def doc_card():
    with open(DOC, encoding="utf-8") as f:
        return json.load(f)["routes"][1]["response"]


class SchemaTests(unittest.TestCase):
    def test_documented_example_is_conform(self):
        self.assertEqual(validate_card_pricing(doc_card()), [])

    def test_missing_provider_and_pricing(self):
        c = doc_card()
        self.assertIn("pricing absent", validate_card_pricing(dict(c, pricing=None))[0])
        self.assertIn("cardmarket absent", validate_card_pricing(dict(c, pricing={"tcgplayer": {}}))[0])

    def test_anomalies_detected(self):
        c = doc_card()
        cm = dict(c["pricing"]["cardmarket"], unit="USD", updated="hier", foo=1, trend=None)
        cm["avg-holo"] = "x"
        issues = validate_card_pricing(dict(c, pricing={"cardmarket": cm}))
        joined = " | ".join(issues)
        for needle in ("devise inattendue", "date updated illisible", "non documentes", "normal.trend absent", "holo.avg non numerique"):
            self.assertIn(needle, joined)


class AdapterTests(unittest.TestCase):
    def adapter(self, http, **kw):
        return TcgdexAdapter(http=http, clock=lambda: NOW, **kw)

    def test_one_observation_per_variant_with_provider_date(self):
        http = FixtureTransport(DOC)
        out = self.adapter(http).search("charizard")
        self.assertEqual([o["product_key"] for o in out],
                         ["tcg:pokemon:swsh3-136:normal", "tcg:pokemon:swsh3-136:holo"])
        self.assertEqual([o["price_eur"] for o in out], [0.08, 0.21])
        self.assertTrue(all(o["evidence_type"] == "MARKET_TREND" for o in out))
        self.assertTrue(all(o["observed_at"].startswith("2025-08-05") for o in out))  # date fournisseur
        self.assertTrue(all(o["market_stats"]["stale"] for o in out))  # > 7 j
        self.assertEqual(out[1]["market_stats"]["avg30"], 0.26)

    def test_bounded_requests_and_pagination(self):
        http = FixtureTransport(DOC)
        ad = self.adapter(http, max_details=2)
        ad.search("charizard", limit=50)
        self.assertEqual(ad.http_calls, 2)  # 1 recherche + 1 detail (1 seule carte listee)
        params = http.log[0][2]
        self.assertEqual((params["pagination:page"], params["pagination:itemsPerPage"]), (1, 2))

    def test_no_assumption_on_missing_values(self):
        for mutate in (lambda cm: cm.pop("unit"), lambda cm: cm.update(updated="?"),
                       lambda cm: cm.update(unit="USD")):
            http = FixtureTransport(DOC)
            cm = http.routes[1]["response"]["pricing"]["cardmarket"]
            mutate(cm)
            self.assertEqual(self.adapter(http).search("charizard"), [])
        http = FixtureTransport(DOC)
        cm = http.routes[1]["response"]["pricing"]["cardmarket"]
        cm["trend-holo"] = None
        self.assertEqual([o["product_key"] for o in self.adapter(http).search("charizard")],
                         ["tcg:pokemon:swsh3-136:normal"])
        http = FixtureTransport(DOC)
        http.routes[1]["response"]["pricing"] = None
        self.assertEqual(self.adapter(http).search("charizard"), [])


class RecordingTests(unittest.TestCase):
    def test_records_raw_and_serves_cache(self):
        with tempfile.TemporaryDirectory() as d:
            t = RecordingCachingTransport(FixtureTransport(DOC), d, clock=lambda: NOW)
            body = t.get("https://api.tcgdex.net/v2/en/cards/swsh3-136")
            t.get("https://api.tcgdex.net/v2/en/cards/swsh3-136")
            s = t.summary()
            self.assertEqual((s["http_requests_executed"], s["served_from_cache"]), (1, 1))
            raw = glob.glob(os.path.join(d, "*.json"))
            with open(raw[0], encoding="utf-8") as f:
                rec = json.load(f)
            self.assertEqual(rec["body"], body)  # corps brut intact
            self.assertNotIn("headers", rec)

    def test_errors_logged_not_cached(self):
        class Dns:
            def get(self, *a, **k):
                raise OSError("Could not resolve host")
        with tempfile.TemporaryDirectory() as d:
            t = RecordingCachingTransport(Dns(), d)
            with self.assertRaises(OSError):
                t.get("https://api.tcgdex.net/v2/en/cards")
            self.assertIn("resolve", t.summary()["errors"][0]["error"])
            t2 = RecordingCachingTransport(FixtureTransport(DOC), d)
            with self.assertRaises(HttpError):
                t2.get("https://api.tcgdex.net/v2/en/unknown")
            self.assertEqual(glob.glob(os.path.join(d, "*.json")), [])


class ProbeTests(unittest.TestCase):
    def test_probe_end_to_end_offline(self):
        from tools.check_public_files import main as check
        from tools.tcgdex_probe import probe
        with tempfile.TemporaryDirectory() as d:
            rep = probe("charizard", 2, d, inner_transport=FixtureTransport(DOC), as_of=NOW)
            self.assertEqual(rep["http"]["http_requests_executed"], 2)
            self.assertEqual(rep["http"]["errors"], [])
            self.assertEqual(rep["schema_issues_by_card"], {"swsh3-136": []})
            self.assertTrue(rep["check_only_market_trend"])
            self.assertTrue(rep["check_no_positive_decision_from_market_trend"])
            self.assertTrue(rep["simulated"])
            self.assertFalse(rep["live"])
            self.assertEqual(rep["decisions"], {})  # aucune offre : aucune investigation
            for f in ("latest.json", "cost_journal.jsonl", "probe_report.json"):
                self.assertTrue(os.path.exists(os.path.join(d, f)), f)
            self.assertEqual(check([os.path.join(d, "latest.json"), os.path.join(d, "cost_journal.jsonl")]), 0)
            with open(os.path.join(d, "latest.json"), encoding="utf-8") as f:
                latest = json.load(f)
            self.assertEqual(latest["campaigns"][0]["status"], "COMPLETED")
            self.assertEqual(latest["summary"]["n_opportunity_alert"], 0)

    def test_probe_refuses_unverified_source(self):
        from tools.tcgdex_probe import probe
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                probe("x", 1, d, inner_transport=FixtureTransport(DOC),
                      registry={"tcgdex": {"env": [], "status": "UNVERIFIED"}})


class NoBuyFromTrendTests(unittest.TestCase):
    def test_offer_far_below_trend_is_watch_at_most(self):
        """Une annonce a -60 % du prix indicatif reste WATCH : jamais BUY."""
        from discovery.pipeline import run_pipeline
        from edge_engine import DEFAULT_CONFIG

        class L:
            def __init__(self, obs):
                self.obs = obs

            def search(self, q, limit=20):
                return [dict(o) for o in self.obs]
        key = "tcg:pokemon:swsh3-136:holo"
        obs = [{"source": "tcgdex", "source_url": "https://api.tcgdex.net/v2/en/cards/swsh3-136",
                "external_id": "t1", "observed_at": "2026-10-17T00:00:00Z", "name": "Pokemon card Charizard holo",
                "product_key": key, "price_eur": 100.0, "evidence_type": "MARKET_TREND", "condition": "new"},
               {"source": "shop", "source_url": "https://shop.example/1", "external_id": "o1",
                "observed_at": "2026-10-18T00:00:00Z", "name": "Charizard holo", "product_key": key,
                "price_eur": 40.0, "shipping_eur": 0, "evidence_type": "ASKING_PRICE", "condition": "new"}]
        with tempfile.TemporaryDirectory() as d:
            out, invs, _ = run_pipeline(
                [{"id": "trend-test", "family": "emerging", "queries": ["q"], "sources": ["a"]}],
                {"a": L(obs)}, dict(DEFAULT_CONFIG, treasury=10000, engaged=0),
                os.path.join(d, "s"), os.path.join(d, "l.json"), os.path.join(d, "p"), as_of=NOW)
        self.assertEqual(len(invs), 1)
        self.assertEqual(invs[0]["decision"], "WATCH")
        self.assertFalse(invs[0]["opportunity_alert"])
        self.assertIsNone(invs[0]["valuation_basis"])
        self.assertEqual(invs[0]["reasons"][0]["type"], "BELOW_MARKET_TREND")


class LiveFixtureTests(unittest.TestCase):
    """Non-regression sur reponses REELLES exportees par la sonde.
    Ignore explicitement tant qu'aucune sonde live n'a ete executee."""

    def test_live_responses_still_parse(self):
        files = glob.glob(os.path.join(LIVE, "*.json"))
        if not files:
            self.skipTest("aucune reponse TCGdex reelle enregistree (lancer tools.tcgdex_probe --export-fixture)")
        for f in files:
            with open(f, encoding="utf-8") as fh:
                rec = json.load(fh)
            if "/cards/" in rec["url"]:
                issues = validate_card_pricing(rec["body"])
                self.assertFalse([i for i in issues if "devise" in i or "illisible" in i], f)


if __name__ == "__main__":
    unittest.main()
