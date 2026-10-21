"""Verrou de depense a la couche d'execution (correctifs post-R4)."""
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone

from discovery.adapters import EbaySoldAdapter
from discovery.campaigns import run_campaign
from investigation.funnel import paid_budget
from investigation.spend import PaidGate, SpendGuard, SpendNotAuthorized, parse_policy

OK = {"authorized": True, "max_usd_per_run": 0.5, "est_usd_per_call": 0.125}


class Counter:
    name = "p"

    def __init__(self):
        self.calls = []

    def search(self, q, limit=20):
        self.calls.append(q)
        return []


class PaidCounter(Counter):
    paid = True


class PolicyValidationTests(unittest.TestCase):
    def test_rejects_non_finite_bool_and_non_positive(self):
        bad = [float("nan"), float("inf"), float("-inf"), "1e400", "nan", True, False, 0, -1, "abc", None, [1]]
        for v in bad:
            for field in ("max_usd_per_run", "est_usd_per_call"):
                pol, why = parse_policy(dict(OK, **{field: v}))
                self.assertIsNone(pol, f"{field}={v!r}")
                self.assertEqual(paid_budget({"paid_investigation": dict(OK, **{field: v})})[0], 0)
        for v in (float("nan"), float("inf"), True, 0):
            self.assertIsNone(parse_policy(dict(OK, max_usd_per_month=v))[0], repr(v))

    def test_authorized_must_be_literal_true(self):
        for v in ("true", 1, "yes", None):
            self.assertIsNone(parse_policy(dict(OK, authorized=v))[0])

    def test_cap_below_one_call(self):
        self.assertIsNone(parse_policy(dict(OK, max_usd_per_run=0.1))[0])

    def test_valid_policy(self):
        pol, _ = parse_policy(OK)
        self.assertEqual(pol["max_calls_per_run"], 4)
        self.assertEqual(parse_policy(dict(OK, est_usd_per_call="0.125"))[0]["max_calls_per_run"], 4)


class ExecutionLayerTests(unittest.TestCase):
    def test_campaign_flag_no_longer_bypasses(self):
        inner = PaidCounter()
        r = run_campaign({"id": "bypass-test", "family": "liquidity", "queries": ["LEGO 1"],
                          "sources": ["p"], "paid_authorized": True}, {"p": inner})
        self.assertEqual(inner.calls, [])
        self.assertEqual(r["run"]["calls"][0]["status"], "SKIPPED_PAID_NOT_AUTHORIZED")

    def test_gate_without_authorization(self):
        inner = Counter()
        gate = PaidGate("p", inner, SpendGuard(None))
        r = run_campaign({"id": "gate-test", "family": "liquidity", "queries": ["LEGO 1"],
                          "sources": ["p"], "paid_authorized": True}, {"p": gate})
        self.assertEqual(inner.calls, [])
        self.assertEqual(r["run"]["calls"][0]["status"], "SKIPPED_PAID_NOT_AUTHORIZED")

    def test_only_funnel_approved_queries_and_run_cap(self):
        with tempfile.TemporaryDirectory() as d:
            inner = Counter()
            g = SpendGuard(OK, ledger_path=os.path.join(d, "spend.jsonl"))
            gate = PaidGate("p", inner, g)
            with self.assertRaises(SpendNotAuthorized):
                gate.search("LEGO 1")  # autorise, mais requete non approuvee
            g.allow([f"LEGO {i}" for i in range(10)])
            # Counter ne consomme pas : aucun appel externe -> reservations liberees
            for i in range(6):
                gate.search(f"LEGO {i}")
            self.assertEqual(g.spent_usd, 0)
            self.assertEqual(len(inner.calls), 6)

    def test_monthly_cap_with_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            led = os.path.join(d, "spend.jsonl")
            clock = lambda: datetime(2026, 10, 18, tzinfo=timezone.utc)
            with open(led, "w", encoding="utf-8") as f:
                for rid, at, usd in (("a", "2026-10-02T00:00:00+00:00", 0.9),
                                     ("b", "2026-09-30T00:00:00+00:00", 50)):
                    f.write(json.dumps({"event": "reserved", "reservation_id": rid, "at": at, "est_usd": usd}) + "\n")
            g = SpendGuard(dict(OK, max_usd_per_month=1.0), ledger_path=led, clock=clock)
            g.allow(["LEGO 1"])
            with self.assertRaises(SpendNotAuthorized):
                g.reserve("p", "LEGO 1")  # 0.9 + 0.125 > 1.0 (septembre ignore)
            g2 = SpendGuard(dict(OK, max_usd_per_month=1.1), ledger_path=led, clock=clock)
            g2.allow(["LEGO 1"])
            g2.reserve("p", "LEGO 1")

    def test_paid_adapter_refuses_direct_call_without_guard(self):
        with self.assertRaises(SpendNotAuthorized):
            EbaySoldAdapter(0.92).search("LEGO 1")

    def test_gate_requires_real_guard(self):
        with self.assertRaises(TypeError):
            PaidGate("p", Counter(), {"authorized": True})


class ConfigSourceTests(unittest.TestCase):
    def test_public_config_authorization_ignored(self):
        from edge_engine import load_config
        with tempfile.TemporaryDirectory() as d:
            pub = os.path.join(d, "config.json")
            with open(pub, "w", encoding="utf-8") as f:
                json.dump({"paid_investigation": OK}, f)
            cfg = load_config(pub, private_path=os.path.join(d, "absent.json"))
            self.assertNotIn("paid_investigation", cfg)
            self.assertTrue(cfg["_config_warnings"])

    def test_guard_reads_private_file_only(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "config.private.json")
            self.assertIsNone(SpendGuard.from_private_file(p).policy)
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"paid_investigation": OK}, f)
            self.assertEqual(SpendGuard.from_private_file(p).max_calls, 4)

    def test_public_file_with_authorization_flagged(self):
        from tools.check_public_files import check_file
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"paid_investigation": {"authorized": True}}, f)
            self.assertEqual(len(check_file(p)), 1)
            ex = os.path.join(d, "c.json.example")
            with open(ex, "w", encoding="utf-8") as f:
                json.dump({"paid_investigation": {"authorized": False}}, f)
            self.assertEqual(check_file(ex), [])


if __name__ == "__main__":
    unittest.main()
