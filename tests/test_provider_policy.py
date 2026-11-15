"""Tests offline du registre fournisseur et du verrou SpendGuard."""
import os
import tempfile
import unittest

from intelligence.provider_policy import (
    ProviderPolicyError, execute_paid_provider, provider_assignment,
    provider_metadata,
)
from investigation.spend import SpendGuard, SpendNotAuthorized


VERIFIED_REGISTRY = {
    "openai": {"status": "VERIFIED", "paid": True, "estimated_usd_per_call": 0.1}
}


class FakePaid:
    provider_id = "openai"
    model_id = "model-explicit-test"
    cost_status = "known"
    paid = True
    remote = True
    timeout_support = True

    def __init__(self, guard=None, consume=True):
        self.guard, self.consume = guard, consume
        self.calls = 0

    def execute(self):
        self.calls += 1
        if self.consume:
            self.guard.consume("llm:openai", "approved-analysis")
        return {"ok": True}


class ProviderPolicyTests(unittest.TestCase):
    def guard(self, path, authorized=True, per_call=0.1):
        g = SpendGuard({"authorized": authorized, "max_usd_per_run": 1,
                        "est_usd_per_call": per_call}, ledger_path=path)
        g.allow(["approved-analysis"])
        return g

    def test_paid_provider_never_runs_without_guard(self):
        adapter = FakePaid()
        with self.assertRaises(SpendNotAuthorized):
            execute_paid_provider(adapter, "approved-analysis", None, registry=VERIFIED_REGISTRY)
        self.assertEqual(adapter.calls, 0)

    def test_paid_provider_requires_explicit_spend_authorization(self):
        with tempfile.TemporaryDirectory() as d:
            g = self.guard(os.path.join(d, "ledger.jsonl"), authorized=False)
            adapter = FakePaid(g)
            with self.assertRaises(SpendNotAuthorized):
                execute_paid_provider(adapter, "approved-analysis", g, registry=VERIFIED_REGISTRY)
            self.assertEqual(adapter.calls, 0)

    def test_unverified_registry_blocks_before_execution(self):
        adapter = FakePaid()
        with self.assertRaises(ProviderPolicyError):
            provider_metadata(adapter, registry={"openai": {
                "status": "UNVERIFIED", "paid": True, "estimated_usd_per_call": 0.1}})
        self.assertEqual(adapter.calls, 0)

    def test_missing_registry_cost_blocks_before_execution(self):
        adapter = FakePaid()
        with self.assertRaises(ProviderPolicyError):
            provider_metadata(adapter, registry={"openai": {
                "status": "VERIFIED", "paid": True, "estimated_usd_per_call": None}})
        self.assertEqual(adapter.calls, 0)

    def test_unknown_adapter_cost_is_blocked_before_execution(self):
        class Unknown(FakePaid):
            cost_status = "unknown"
        adapter = Unknown()
        with self.assertRaises(ProviderPolicyError):
            provider_metadata(adapter, registry=VERIFIED_REGISTRY)
        self.assertEqual(adapter.calls, 0)

    def test_missing_model_or_timeout_support_fails_closed(self):
        class Incomplete(FakePaid):
            model_id = None
            timeout_support = False
        with self.assertRaises(ProviderPolicyError):
            provider_metadata(Incomplete(), registry=VERIFIED_REGISTRY)

    def test_spendguard_estimate_cannot_understate_verified_provider_cost(self):
        with tempfile.TemporaryDirectory() as d:
            g = self.guard(os.path.join(d, "ledger.jsonl"), per_call=0.01)
            adapter = FakePaid(g)
            with self.assertRaises(SpendNotAuthorized):
                execute_paid_provider(adapter, "approved-analysis", g, registry=VERIFIED_REGISTRY)
            self.assertEqual(adapter.calls, 0)

    def test_paid_adapter_must_consume_r42_reservation(self):
        with tempfile.TemporaryDirectory() as d:
            g = self.guard(os.path.join(d, "ledger.jsonl"))
            adapter = FakePaid(g, consume=False)
            with self.assertRaises(SpendNotAuthorized):
                execute_paid_provider(adapter, "approved-analysis", g, registry=VERIFIED_REGISTRY)
            self.assertEqual(adapter.calls, 1)
            self.assertEqual(g.spent_usd, 0)

    def test_authorized_paid_adapter_consumes_exactly_one_reservation(self):
        with tempfile.TemporaryDirectory() as d:
            g = self.guard(os.path.join(d, "ledger.jsonl"))
            adapter = FakePaid(g)
            self.assertEqual(execute_paid_provider(
                adapter, "approved-analysis", g, registry=VERIFIED_REGISTRY), {"ok": True})
            self.assertEqual(adapter.calls, 1)
            self.assertAlmostEqual(g.spent_usd, 0.1)

    def test_role_assignment_is_declarative_and_has_no_model(self):
        assignment = provider_assignment("market_intelligence")
        self.assertEqual(assignment["execution_status"], "not_configured")
        self.assertIsNone(assignment["model_id"])
        self.assertTrue(assignment["preferred_providers"])


if __name__ == "__main__":
    unittest.main()
