"""Offline tests for the trusted per-user inquiry gateway."""
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from intelligence.inquiry_gateway import run_user_inquiry, InquiryAccessDenied
from intelligence.usage_meter import InMemoryUsageStore, UsageLimitExceeded


NOW = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)


class FreeProvider:
    name = "offline-test"
    paid = False


class PaidProvider:
    name = "paid-test"
    paid = True


class InquiryGatewayTests(unittest.TestCase):
    def invoke(self, usage_store, **overrides):
        args = {
            "question": "Analyse Pokémon TCG",
            "corpora": [],
            "report_store": object(),
            "user_id": "user-123",
            "request_id": "request-1",
            "usage_store": usage_store,
            "provider": FreeProvider(),
            "now": NOW,
            "allow_test_store": True,
        }
        args.update(overrides)
        return run_user_inquiry(**args)

    @patch("intelligence.inquiry.run_inquiry", return_value={"status": "REPORT"})
    def test_reserves_quota_and_calls_existing_engine(self, run):
        usage = InMemoryUsageStore()
        result = self.invoke(usage)
        run.assert_called_once()
        self.assertEqual(result["status"], "REPORT")
        self.assertEqual(result["usage"]["metric"], "investigation")
        self.assertEqual(result["usage"]["limit"], 3)
        self.assertEqual(result["usage"]["period_utc"], "2026-11-15")

    @patch("intelligence.inquiry.run_inquiry", return_value={"status": "REPORT"})
    def test_free_daily_quota_is_enforced_before_second_new_request(self, run):
        usage = InMemoryUsageStore()
        for i in range(3):
            self.invoke(usage, request_id=f"request-{i}")
        with self.assertRaises(InquiryAccessDenied):
            self.invoke(usage, request_id="request-over-limit")
        self.assertEqual(run.call_count, 3)

    @patch("intelligence.inquiry.run_inquiry", return_value={"status": "REPORT"})
    def test_same_request_id_is_quota_idempotent(self, run):
        usage = InMemoryUsageStore()
        self.invoke(usage)
        self.invoke(usage)
        # The usage store reserves one unit for the same idempotency key.
        self.assertEqual(len(usage._reservations), 1)
        # Execution deduplication is intentionally left to the HTTP caller.
        self.assertEqual(run.call_count, 2)

    def test_paid_provider_cannot_be_used_by_free_user(self):
        usage = InMemoryUsageStore()
        with self.assertRaises(InquiryAccessDenied):
            self.invoke(usage, provider=PaidProvider())
        self.assertEqual(len(usage._reservations), 0)

    def test_test_only_store_is_rejected_unless_explicitly_enabled(self):
        with self.assertRaises(InquiryAccessDenied):
            self.invoke(InMemoryUsageStore(), allow_test_store=False)

    def test_missing_server_identity_is_rejected(self):
        with self.assertRaises(InquiryAccessDenied):
            self.invoke(InMemoryUsageStore(), user_id="")

    def test_missing_usage_store_is_rejected(self):
        with self.assertRaises(InquiryAccessDenied):
            self.invoke(None)

    @patch("intelligence.inquiry.run_inquiry", return_value={"status": "REPORT"})
    def test_premium_uses_premium_daily_limit(self, run):
        usage = InMemoryUsageStore()
        claim = {
            "verified": True,
            "plan": "premium",
            "status": "active",
            "period_end": "2026-12-01T00:00:00Z",
        }
        for i in range(20):
            self.invoke(
                usage,
                request_id=f"premium-{i}",
                subscription_claim=claim,
            )
        with self.assertRaises(InquiryAccessDenied):
            self.invoke(
                usage,
                request_id="premium-over-limit",
                subscription_claim=claim,
            )
        self.assertEqual(run.call_count, 20)


if __name__ == "__main__":
    unittest.main()
