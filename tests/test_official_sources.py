"""R4 : sources officielles, types de preuves, agregats, entonnoir payant, pilote LEGO."""
import json
import os
import tempfile
import unittest
from datetime import date, datetime, timezone

from discovery.access import GatedAdapter, access_status, load_registry
from discovery.adapters import SourceUnavailable
from discovery.adapters_official import (BrickLinkAdapter, BricksetAdapter, EbayBrowseAdapter,
                                         HttpError, TcgdexAdapter, _oauth1_header)
from discovery.campaigns import run_campaign
from discovery.engine import normalize
from discovery.fixture_http import FixtureTransport
from edge_engine import DEFAULT_CONFIG
from investigation.aggregate import DEFAULT_POLICY, assess, reference_prices
from investigation.analysis import economic_decision
from investigation.funnel import eligible, paid_budget

ROOT = os.path.join(os.path.dirname(__file__), "..")
ROUTES = os.path.join(ROOT, "discovery", "fixtures", "pilot_lego", "http_routes.json")
AS_OF = datetime(2026, 10, 18, 9, tzinfo=timezone.utc)
ENV_ALL = {"EBAY_CLIENT_ID": "id", "EBAY_CLIENT_SECRET": "s", "BRICKSET_API_KEY": "k",
           "BRICKLINK_CONSUMER_KEY": "a", "BRICKLINK_CONSUMER_SECRET": "b",
           "BRICKLINK_TOKEN": "c", "BRICKLINK_TOKEN_SECRET": "d"}


def agg_obs(tq=42, lots=18, avg=410, qavg=398, mn=330, mx=520, day="2026-10-18", region="europe"):
    o, err = normalize({
        "source": "bricklink", "source_url": "https://www.bricklink.com/x", "external_id": f"a{tq}{mn}",
        "observed_at": f"{day}T08:00:00Z", "name": "LEGO 90001", "product_key": "lego:90001",
        "price_eur": qavg, "evidence_type": "SOLD_AGGREGATE",
        "aggregate": {"period_days": 182, "total_quantity": tq, "lots": lots, "avg_price_eur": avg,
                      "qty_avg_price_eur": qavg, "min_price_eur": mn, "max_price_eur": mx,
                      "condition": "NEW", "region": region}})
    assert err is None, err
    return o


class EvidenceTypeTests(unittest.TestCase):
    base = {"source": "s", "source_url": "https://e.com/1", "external_id": "1",
            "observed_at": "2026-10-18T00:00:00Z", "name": "LEGO 90001", "product_key": "lego:90001"}

    def test_aggregate_requires_explicit_stats(self):
        _, err = normalize(dict(self.base, price_eur=10, evidence_type="SOLD_AGGREGATE", aggregate={"period_days": 182}))
        self.assertEqual(err, "invalid:sold_aggregate")

    def test_aggregate_incoherent_prices_rejected(self):
        bad = {"period_days": 182, "total_quantity": 5, "lots": 2, "avg_price_eur": 500,
               "qty_avg_price_eur": 100, "min_price_eur": 200, "max_price_eur": 300, "condition": "NEW"}
        _, err = normalize(dict(self.base, price_eur=100, evidence_type="SOLD_AGGREGATE", aggregate=bad))
        self.assertEqual(err, "invalid:sold_aggregate")

    def test_used_aggregate_rejected(self):
        a = {"period_days": 182, "total_quantity": 5, "lots": 2, "avg_price_eur": 100,
             "qty_avg_price_eur": 100, "min_price_eur": 90, "max_price_eur": 110, "condition": "USED"}
        _, err = normalize(dict(self.base, price_eur=100, evidence_type="SOLD_AGGREGATE", aggregate=a))
        self.assertEqual(err, "rejected:used_condition")

    def test_availability_and_signal_need_no_price(self):
        o, err = normalize(dict(self.base, evidence_type="AVAILABILITY",
                                availability={"region": "DE", "retail_price_eur": 99.99, "date_last": "2025-06-30"}))
        self.assertIsNone(err)
        self.assertIsNone(o["price_eur"])
        o, err = normalize(dict(self.base, evidence_type="CULTURAL_SIGNAL", signal={"metric": "trends", "value": 1.4}))
        self.assertIsNone(err)

    def test_all_seven_types_declared(self):
        from discovery.engine import EVIDENCE_TYPES
        self.assertEqual(EVIDENCE_TYPES, {"ASKING_PRICE", "RETAIL_OFFER", "SOLD", "SOLD_AGGREGATE",
                                          "MARKET_TREND", "AVAILABILITY", "CULTURAL_SIGNAL"})


class AggregateTests(unittest.TestCase):
    def test_qualifying_aggregate(self):
        r = assess(agg_obs(), date(2026, 10, 18), DEFAULT_POLICY, "lego:90001")
        self.assertTrue(r["qualifies_buy"])
        self.assertIn("pas des ventes individuelles", r["nature"])

    def test_each_criterion_can_fail(self):
        cases = {"fraicheur": dict(day="2026-09-01"), "quantite_vendue": dict(tq=6, lots=3),
                 "lots_distincts": dict(lots=2), "dispersion": dict(mn=50, mx=900),
                 "coherence_moyennes": dict(avg=500, qavg=380, mn=330, mx=520),
                 "region": dict(region="north_america")}
        for name, kw in cases.items():
            r = assess(agg_obs(**kw), date(2026, 10, 18), DEFAULT_POLICY, "lego:90001")
            self.assertFalse(r["qualifies_buy"], name)
            self.assertIn(name, r["failed"], name)

    def test_wrong_product_fails_exact_match(self):
        r = assess(agg_obs(), date(2026, 10, 18), DEFAULT_POLICY, "lego:12345")
        self.assertIn("correspondance_exacte", r["failed"])

    def test_reference_prices_never_use_raw_extremes(self):
        ref = reference_prices(agg_obs(), DEFAULT_POLICY)
        self.assertEqual(ref["central"][0], 398)
        self.assertEqual(ref["prudent"][0], round(398 * 0.9, 2))
        self.assertEqual(ref["favorable"][0], 410)  # pas 520 (max brut)

    def test_aggregate_basis_caps_at_buy(self):
        scen = {"prudent": {"net_roi_pct": 60}, "central": {"net_roi_pct": 80}}
        self.assertEqual(economic_decision(scen, "HIGH", 20, True, True, basis="SOLD_AGGREGATE")[0], "BUY")
        self.assertEqual(economic_decision(scen, "HIGH", 20, True, True)[0], "STRONG_BUY")
        self.assertEqual(economic_decision(scen, "HIGH", 20, False, True, basis="SOLD_AGGREGATE")[0], "WATCH")


class AdapterParsingTests(unittest.TestCase):
    def setUp(self):
        self.http = FixtureTransport(ROUTES)

    def test_ebay_browse_token_condition_and_shipping(self):
        ad = EbayBrowseAdapter(http=self.http, environ=ENV_ALL)
        out = ad.search("LEGO Icons")
        self.assertEqual(len(out), 5)
        self.assertTrue(all(o["evidence_type"] == "ASKING_PRICE" for o in out))
        b = next(o for o in out if o["external_id"] == "v1|1002|0")
        self.assertEqual((b["price_eur"], b["shipping_eur"]), (59.0, 4.99))
        used = next(o for o in out if o["external_id"] == "v1|1005|0")
        self.assertIsNone(normalize(used)[0])  # annonce d'occasion rejetee
        ad.search("LEGO Icons")
        self.assertEqual(sum(1 for m, *_ in self.http.log if m == "POST"), 1)  # jeton reutilise
        get = [p for m, u, p in self.http.log if m == "GET"][0]
        self.assertEqual(get["filter"], "conditionIds:{1000}")

    def test_ebay_browse_requires_credentials(self):
        with self.assertRaises(SourceUnavailable):
            EbayBrowseAdapter(http=self.http, environ={}).search("LEGO Icons")

    def test_bricklink_aggregate_and_no_sales(self):
        ad = BrickLinkAdapter(http=self.http, environ=ENV_ALL)
        o = ad.search("LEGO 90001")[0]
        self.assertEqual(o["evidence_type"], "SOLD_AGGREGATE")
        self.assertEqual((o["aggregate"]["total_quantity"], o["aggregate"]["lots"]), (42, 18))
        self.assertIsNone(normalize(o)[1])
        self.assertEqual(ad.search("LEGO 90004"), [])  # 0 vente : aucune observation inventee
        self.assertFalse(ad.accepts("LEGO Icons fictif"))
        url, params = [(u, p) for m, u, p in self.http.log][0]
        self.assertEqual(params["guide_type"], "sold")
        self.assertEqual(params["new_or_used"], "N")

    def test_bricklink_api_error_is_explicit(self):
        http = FixtureTransport(ROUTES)
        http.routes.insert(0, {"method": "GET", "url": BrickLinkAdapter.BASE + "/items/SET/90001-1/price",
                               "response": {"meta": {"code": 401, "message": "BAD_OAUTH_REQUEST"}}})
        with self.assertRaises(HttpError):
            BrickLinkAdapter(http=http, environ=ENV_ALL).search("LEGO 90001")

    def test_oauth1_signature_reference_vector(self):
        # Vecteur de reference public (documentation OAuth 1.0a de Twitter).
        h = _oauth1_header("POST", "https://api.twitter.com/1.1/statuses/update.json",
                           {"include_entities": "true", "status": "Hello Ladies + Gentlemen, a signed OAuth request!"},
                           "xvz1evFS4wEEPTGEFPHBog", "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw",
                           "370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb",
                           "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE",
                           nonce="kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg", timestamp=1318622958)
        self.assertIn('oauth_signature="hCtSmYh%2BiHYCEqBWrE7C7hYmtUk%3D"', h)

    def test_brickset_availability(self):
        o = BricksetAdapter(http=self.http, environ=ENV_ALL).search("LEGO 90004")[0]
        self.assertEqual(o["evidence_type"], "AVAILABILITY")
        self.assertEqual(o["availability"]["date_last"], "2025-06-30")
        self.assertEqual(normalize(o)[0]["availability"]["retail_price_eur"], 99.99)

    def test_tcgdex_market_trend_only(self):
        out = TcgdexAdapter(http=self.http).search("Dracaufeu Fictif")
        self.assertEqual([o["product_key"] for o in out], ["tcg:pokemon:fx1-001:normal"])
        self.assertEqual(out[0]["evidence_type"], "MARKET_TREND")
        self.assertEqual(out[0]["price_eur"], 40.0)

    def test_actor_input_matches_public_examples(self):
        from connectors.ebay import actor_input
        a = actor_input("LEGO 10316", 50)
        self.assertEqual((a["keywords"], a["count"]), (["LEGO 10316"], 50))
        self.assertNotIn("keyword", a)


class AccessGateTests(unittest.TestCase):
    def test_registry_blocks_unverified_and_missing_credentials(self):
        reg = load_registry()
        # Seul TCGdex a ete verifie (pilote) ; les autres restent bloquees.
        self.assertEqual({k for k, s in reg.items() if s["status"] == "VERIFIED"}, {"tcgdex"})
        st = access_status("bricklink", reg, environ={})
        self.assertFalse(st["usable"])
        self.assertIn("non verifies", st["reason"])
        self.assertIn("BRICKLINK_TOKEN", st["reason"])
        reg2 = {k: dict(v, status="VERIFIED") for k, v in reg.items()}
        self.assertTrue(access_status("tcgdex", reg2, environ={})["usable"])

    def test_gated_adapter_quota_and_unavailability(self):
        class Inner:
            name = "tcgdex"

            def search(self, q, limit):
                return []
        reg = {"tcgdex": {"env": [], "status": "VERIFIED", "quota_per_run": 2}}
        g = GatedAdapter("tcgdex", Inner(), reg, {})
        g.search("a"), g.search("b")
        with self.assertRaises(SourceUnavailable):
            g.search("c")
        r = run_campaign({"id": "gate-test", "family": "emerging", "queries": ["x"], "sources": ["tcgdex"]},
                         {"tcgdex": GatedAdapter("tcgdex", Inner(), {"tcgdex": {"env": [], "status": "UNVERIFIED"}}, {})})
        self.assertEqual(r["run"]["calls"][0]["status"], "SKIPPED_UNAVAILABLE")
        self.assertEqual(r["run"]["status"], "FAILED")

    def test_real_mode_nothing_usable_without_setup(self):
        from discovery.cli import build_adapters
        from investigation.spend import SpendNotAuthorized
        ads = build_adapters(environ={})
        # TCGdex (verifie, sans cle) est utilisable : on ne l'appelle pas ici
        # (aucun appel reseau pendant les tests), on verifie son statut.
        from discovery.access import access_status, load_registry
        self.assertTrue(access_status("tcgdex", load_registry(), environ={})["usable"])
        for name, ad in ads.items():
            if name == "tcgdex":
                continue
            with self.assertRaises((SourceUnavailable, SpendNotAuthorized), msg=name):
                ad.search("LEGO 10316")


class PaidFunnelTests(unittest.TestCase):
    def test_budget_rules(self):
        self.assertEqual(paid_budget({})[0], 0)
        self.assertEqual(paid_budget({"paid_investigation": {"authorized": True, "max_usd_per_run": 1}})[0], 0)
        self.assertEqual(paid_budget({"paid_investigation": {"authorized": True, "max_usd_per_run": 1,
                                                             "est_usd_per_call": 0.125}})[0], 8)
        self.assertEqual(paid_budget({"paid_investigation": {"authorized": "yes", "max_usd_per_run": 9,
                                                             "est_usd_per_call": 1}})[0], 0)

    def test_paid_source_never_called_without_authorization(self):
        calls = []

        class Paid:
            paid = True

            def search(self, q, limit):
                calls.append(q)
                return []
        r = run_campaign({"id": "paid-test", "family": "liquidity", "queries": ["LEGO 1"], "sources": ["p"]},
                         {"p": Paid()})
        self.assertEqual(calls, [])
        self.assertEqual(r["run"]["calls"][0]["status"], "SKIPPED_PAID_NOT_AUTHORIZED")

    def test_eligibility_excludes_already_confirmed(self):
        invs = [{"product_key": "lego:1", "decision": "BUY", "best_offer": {"total_eur": 1}, "valuation_basis": "SOLD_AGGREGATE"},
                {"product_key": "lego:2", "decision": "BUY", "best_offer": {"total_eur": 1}, "valuation_basis": "INDIVIDUAL_SALES"},
                {"product_key": "lego:3", "decision": "WAIT", "best_offer": {"total_eur": 1}},
                {"product_key": "lego:4", "decision": "WATCH", "best_offer": None}]
        self.assertEqual(eligible(invs), ["lego:1"])


class LegoPilotTests(unittest.TestCase):
    def run_pilot(self, d, config=None, guard=None):
        from discovery.cli import build_adapters
        from discovery.pipeline import run_pipeline
        with open(os.path.join(ROOT, "discovery", "pilot_lego_campaigns.json"), encoding="utf-8") as f:
            camps = json.load(f)["campaigns"]
        ads = build_adapters(offline_http=ROUTES, spend_guard=guard, as_of=AS_OF)
        return run_pipeline(camps, ads, config or dict(DEFAULT_CONFIG), os.path.join(d, "s"),
                            os.path.join(d, "latest.json"), os.path.join(d, "p"), as_of=AS_OF,
                            cost_journal_path=os.path.join(d, "cost.jsonl"), spend_guard=guard)

    def test_pilot_outcomes(self):
        with tempfile.TemporaryDirectory() as d:
            out, invs, _ = self.run_pilot(d)
            dec = {i["product_key"]: i["decision"] for i in invs}
            self.assertEqual(dec, {"lego:90001": "BUY", "lego:90002": "WATCH",
                                   "lego:90003": "WATCH", "lego:90004": "NO_DATA"})
            i1 = next(i for i in invs if i["product_key"] == "lego:90001")
            self.assertEqual(i1["valuation_basis"], "SOLD_AGGREGATE")
            self.assertFalse(i1["funding"]["execution_ready"])  # capital inconnu
            self.assertTrue(out["simulated"])
            # Pokemon scelle : aucune valorisation inventee, aucune decision positive
            pk = {p["product_key"]: p for p in out["products"]}
            sealed = pk["name:pokemon-display-fictive-36-boosters"]
            self.assertNotIn("investigation", sealed)
            self.assertIn("aucune vente conclue observee : prix de revente inconnu", sealed["risks"])
            # source payante bloquee, explicitement
            calls = [c for r in out["campaigns"] for c in r["calls"]]
            self.assertTrue(any(c["status"] == "SKIPPED_PAID_NOT_AUTHORIZED" for c in calls))
            self.assertFalse(out["paid_confirmation"]["executed"])
            # aucune erreur artificielle due a des requetes inadaptees
            self.assertFalse(any(c["status"] == "ERROR" for c in calls))
            from tools.check_public_files import main as check
            self.assertEqual(check([os.path.join(d, "latest.json"), os.path.join(d, "s")]), 0)

    def test_authorization_in_merged_config_is_ignored(self):
        # R4 acceptait l'autorisation via la config fusionnee : plus maintenant.
        cfg = dict(DEFAULT_CONFIG, paid_investigation={"authorized": True, "max_usd_per_run": 0.25,
                                                       "est_usd_per_call": 0.125})
        with tempfile.TemporaryDirectory() as d:
            out, _, _ = self.run_pilot(d, cfg)
            self.assertFalse(out["paid_confirmation"]["executed"])

    def test_replay_independent_of_wall_clock(self):
        """Regression (19/10/2026) : un rejeu execute un autre jour que as_of
        datait les observations a l'horloge murale -> 'futur' -> BUY perdu."""
        from unittest import mock
        import discovery.adapters_official as ao
        with mock.patch.object(ao, "_now", lambda: "2027-01-01T00:00:00+00:00"), \
             tempfile.TemporaryDirectory() as d:
            _, invs, _ = self.run_pilot(d)
        self.assertEqual({i["product_key"]: i["decision"] for i in invs}["lego:90001"], "BUY")

    def test_paid_confirmation_respects_cap_when_authorized(self):
        from investigation.spend import SpendGuard
        with tempfile.TemporaryDirectory() as d:
            guard = SpendGuard({"authorized": True, "max_usd_per_run": 0.25, "est_usd_per_call": 0.125},
                               ledger_path=os.path.join(d, "spend.jsonl"))
            out, _, _ = self.run_pilot(d, guard=guard)
            pc = out["paid_confirmation"]
            self.assertTrue(pc["executed"])
            self.assertLessEqual(pc["calls_executed"], 2)
            self.assertNotIn("est_usd_spent", pc)  # aucun montant publie
            self.assertNotIn("USD", pc["reason"])
            with open(os.path.join(d, "spend.jsonl"), encoding="utf-8") as f:
                events = [json.loads(l) for l in f]
            reserved = [e for e in events if e["event"] == "reserved"]
            self.assertLessEqual(len(reserved), 2)
            self.assertTrue(all(e["query"].startswith("LEGO 900") for e in reserved))
            with open(os.path.join(d, "cost.jsonl"), encoding="utf-8") as f:
                self.assertNotIn("USD", f.read())
            with open(os.path.join(d, "cost.jsonl"), encoding="utf-8") as f:
                rows = [json.loads(l) for l in f]
            self.assertTrue(any(r.get("paid") for r in rows))


if __name__ == "__main__":
    unittest.main()
