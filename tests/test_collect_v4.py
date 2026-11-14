"""Integration hors reseau de collect.run() : connecteurs simules."""
import json
import os
import tempfile
import unittest
from unittest import mock

import collect


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()
import edge_engine as E


def ebay_snap(median):
    return {"source": "ebay_sold_us", "captured_at": "2026-10-18T00:00:00",
            "sold_price_median": median, "sold_price_avg": median,
            "sold_count_30d": 12, "lowest_ask": median * 0.9,
            "currency": "USD", "_n_filtered": 30}


class CollectRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = os.getcwd()
        os.chdir(self.tmp.name)
        self.sent = []
        self.cfg = {**E.DEFAULT_CONFIG, "treasury": 300, "engaged": 0,
                    "enabled_sources": {"ebay": True, "cardmarket": True,
                                        "trends": False, "reddit": False,
                                        "scavio": True}}
        self.patches = [
            mock.patch.object(collect, "load_config", lambda: dict(self.cfg)),
            mock.patch.object(collect, "send_message", self.sent.append),
            mock.patch("connectors.telegram.send_message", self.sent.append),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        os.chdir(self.old)
        self.tmp.cleanup()

    def radar(self):
        with open("radar.json", encoding="utf-8") as f:
            return json.load(f)

    def test_all_sources_failing_is_failed_not_cash(self):
        boom = mock.Mock(side_effect=RuntimeError("APIFY_TOKEN absent"))
        with mock.patch.object(collect, "fetch_one", boom), \
             mock.patch.object(collect, "fetch_scavio_offers", boom):
            collect.run()
        r = self.radar()
        self.assertEqual(r["summary"]["decision"], "FAILED")
        self.assertNotEqual(r["summary"]["posture"], "CASH")
        self.assertTrue(all(p["decision"] == "ERROR" for p in r["products"]))
        digest = self.sent[-1]
        self.assertNotIn("CASH", digest)
        E.assert_no_private_leak(r)
        self.assertNotIn("config", r)

    def test_signal_kept_when_capital_insufficient(self):
        # 77073 : cible strong 50 EUR ; 50 USD * 0.92 = 46 EUR -> STRONG_BUY
        def fetch(item):
            return ebay_snap(50) if item["id"] == "lego_77073" else ebay_snap(1000)
        self.cfg["treasury"] = 10  # capital tres insuffisant
        with mock.patch.object(collect, "fetch_one", fetch), \
             mock.patch.object(collect, "fetch_scavio_offers", lambda *a, **k: None):
            collect.run()
        r = self.radar()
        p = next(x for x in r["products"] if x["id"] == "lego_77073")
        self.assertEqual(p["decision"], "STRONG_BUY")
        self.assertTrue(p["opportunity_alert"])
        self.assertEqual(r["summary"]["decision"], "1 SIGNAL")
        self.assertTrue(any("STRONG BUY" in m for m in self.sent))
        with open(os.path.join("private", "run_private.json"), encoding="utf-8") as f:
            priv = json.load(f)
        f77 = next(x for x in priv["funding"] if x["id"] == "lego_77073")
        self.assertFalse(f77["capital_sufficient"])
        self.assertFalse(f77["execution_ready"])
        E.assert_no_private_leak(r)
        raw = read("radar.json")
        self.assertNotIn("treasury", raw)

    def test_verified_offer_enables_execution(self):
        self.cfg["treasury"] = 1000
        def fetch(item):
            return ebay_snap(50) if item["id"] == "lego_77073" else ebay_snap(1000)
        def scavio(query, **kw):
            if "77073" not in query:
                return None
            return {"n_offers": 2, "min_price_eur": 45.0, "offers": [
                {"title": "LEGO 77073 Battle Bus", "price_eur": 45.0,
                 "product_link": "https://shop.example/77073", "seller": "Shop"},
                {"title": "Autre produit", "price_eur": 5.0,
                 "product_link": "https://shop.example/x", "seller": "Shop"}]}
        with mock.patch.object(collect, "fetch_one", fetch), \
             mock.patch.object(collect, "fetch_scavio_offers", scavio):
            collect.run()
        with open(os.path.join("private", "run_private.json"), encoding="utf-8") as f:
            priv = json.load(f)
        f77 = next(x for x in priv["funding"] if x["id"] == "lego_77073")
        self.assertEqual(f77["verified_offer"]["price_eur"], 45.0)  # pas l'offre hors produit
        self.assertTrue(f77["execution_ready"])

    def test_full_coverage_without_signal_is_cash(self):
        self.cfg["enabled_sources"]["scavio"] = False
        with mock.patch.object(collect, "fetch_one", lambda item: ebay_snap(5000)):
            collect.run()
        r = self.radar()
        self.assertEqual(r["summary"]["decision"], "CASH")
        self.assertIn("CASH", self.sent[-1])

    def test_secret_not_leaked_in_error(self):
        os.environ["APIFY_TOKEN"] = "supersecrettoken123"
        try:
            boom = mock.Mock(side_effect=RuntimeError("401 for url ?" + "token" + "=supersecrettoken123"))
            with mock.patch.object(collect, "fetch_one", boom), \
                 mock.patch.object(collect, "fetch_scavio_offers", lambda *a, **k: None):
                collect.run()
            raw = read("radar.json")
            self.assertNotIn("supersecrettoken123", raw)
        finally:
            del os.environ["APIFY_TOKEN"]


if __name__ == "__main__":
    unittest.main()
