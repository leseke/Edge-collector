"""Offline tests for EDGE Free/Premium routing and usage limits."""
import unittest
from datetime import datetime, timezone

from intelligence.subscription_entitlements import (resolve_entitlements, authorize_agent_provider,
                                                       EntitlementError, FREE, PREMIUM)
from intelligence.provider_router import route_provider, ProviderRouteDenied
from intelligence.usage_meter import InMemoryUsageStore, reserve_usage, UsageLimitExceeded


NOW = datetime(2026, 11, 15, tzinfo=timezone.utc)
FREE_REGISTRY = {
    "local_model": {"status": "VERIFIED", "paid": False, "cost_status": "verified_zero",
                    "estimated_usd_per_call": 0, "commercial_use": True, "quota_per_day": 100},
    "free_api": {"status": "VERIFIED", "paid": False, "cost_status": "verified_zero",
                 "estimated_usd_per_call": 0, "commercial_use": True, "quota_per_day": 20},
    "unknown_free": {"status": "UNVERIFIED", "paid": False, "cost_status": "verified_zero",
                     "estimated_usd_per_call": 0, "commercial_use": True, "quota_per_day": 20},
    "paid_api": {"status": "VERIFIED", "paid": True, "cost_status": "verified",
                 "estimated_usd_per_call": 0.02, "commercial_use": True, "quota_per_day": 1000},
}


class SubscriptionEntitlementTests(unittest.TestCase):
    def test_default_is_free(self):
        self.assertEqual(resolve_entitlements(now=NOW)["plan"], FREE)

    def test_client_claim_without_verification_cannot_unlock_premium(self):
        e = resolve_entitlements({"plan": PREMIUM, "status": "active"}, now=NOW)
        self.assertEqual(e["plan"], FREE)
        self.assertFalse(e["paid_provider_access"])

    def test_verified_active_subscription_unlocks_premium(self):
        e = resolve_entitlements({"verified": True, "plan": PREMIUM, "status": "active",
                                  "period_end": "2026-12-15T00:00:00Z"}, now=NOW)
        self.assertEqual(e["plan"], PREMIUM)
        self.assertTrue(e["paid_provider_access"])

    def test_paid_agent_requires_verified_premium_entitlement(self):
        class PaidAgent:
            paid = True
        with self.assertRaises(EntitlementError):
            authorize_agent_provider(resolve_entitlements(now=NOW), PaidAgent())
        premium = resolve_entitlements({"verified": True, "plan": PREMIUM, "status": "active",
                                        "period_end": "2026-12-15T00:00:00Z"}, now=NOW)
        self.assertEqual(authorize_agent_provider(premium, PaidAgent()), "premium_paid_candidate")

    def test_expired_subscription_falls_back_to_free(self):
        e = resolve_entitlements({"verified": True, "plan": PREMIUM, "status": "active",
                                  "period_end": "2026-11-14T00:00:00Z"}, now=NOW)
        self.assertEqual(e["plan"], FREE)

    def test_free_can_route_only_verified_zero_cost_provider(self):
        e = resolve_entitlements(now=NOW)
        decision = route_provider(e, "free_api", FREE_REGISTRY, {"calls_today": 4})
        self.assertTrue(decision["allowed"])
        self.assertEqual(decision["billing"], "zero_cost_verified")

    def test_free_rejects_paid_provider(self):
        with self.assertRaises(ProviderRouteDenied):
            route_provider(resolve_entitlements(now=NOW), "paid_api", FREE_REGISTRY)

    def test_free_rejects_unverified_provider(self):
        with self.assertRaises(ProviderRouteDenied):
            route_provider(resolve_entitlements(now=NOW), "unknown_free", FREE_REGISTRY)

    def test_free_rejects_missing_commercial_permission(self):
        registry = {"x": dict(FREE_REGISTRY["free_api"], commercial_use=False)}
        with self.assertRaises(ProviderRouteDenied):
            route_provider(resolve_entitlements(now=NOW), "x", registry)

    def test_provider_daily_quota_is_enforced(self):
        with self.assertRaises(ProviderRouteDenied):
            route_provider(resolve_entitlements(now=NOW), "free_api", FREE_REGISTRY, {"calls_today": 20})

    def test_premium_paid_provider_requires_budget_and_verified_cost(self):
        e = resolve_entitlements({"verified": True, "plan": PREMIUM, "status": "active",
                                  "period_end": "2026-12-15T00:00:00Z"}, now=NOW)
        with self.assertRaises(ProviderRouteDenied):
            route_provider(e, "paid_api", FREE_REGISTRY, estimated_cost_usd=0.03)
        decision = route_provider(e, "paid_api", FREE_REGISTRY, estimated_cost_usd=0.03,
                                  premium_budget_remaining_usd=0.10)
        self.assertEqual(decision["execution"], "requires_spendguard_r42")

    def test_premium_paid_provider_cannot_exceed_budget_or_understate_cost(self):
        e = resolve_entitlements({"verified": True, "plan": PREMIUM, "status": "active",
                                  "period_end": "2026-12-15T00:00:00Z"}, now=NOW)
        with self.assertRaises(ProviderRouteDenied):
            route_provider(e, "paid_api", FREE_REGISTRY, estimated_cost_usd=0.11,
                           premium_budget_remaining_usd=0.10)
        with self.assertRaises(ProviderRouteDenied):
            route_provider(e, "paid_api", FREE_REGISTRY, estimated_cost_usd=0.01,
                           premium_budget_remaining_usd=0.10)

    def test_usage_store_enforces_limit_and_idempotency(self):
        store = InMemoryUsageStore()
        first = reserve_usage(store, "u1", "2026-11-15", "search", 1, "req-1")
        again = reserve_usage(store, "u1", "2026-11-15", "search", 1, "req-1")
        self.assertEqual(first, again)
        with self.assertRaises(UsageLimitExceeded):
            reserve_usage(store, "u1", "2026-11-15", "search", 1, "req-2")

    def test_usage_store_is_explicitly_test_only(self):
        self.assertTrue(InMemoryUsageStore.test_only)


if __name__ == "__main__":
    unittest.main()
