import unittest
from intelligence.sales_source_typing import classify_sales_observations
R={"evidence_id":"e1","record_type":"ASK","product_key":"pokemon-card-fr","source_url":"https://example.org/listing",
"observed_at":"2026-10-25T09:00:00Z","amount_eur":"42.90","proof_sha256":"a"*64}
class SalesSourceTypingTests(unittest.TestCase):
 def test_ask_is_not_sale(self):
  x=classify_sales_observations([R],as_of="2026-10-25T10:00:00Z")
  self.assertEqual(x["counts"]["ASK"],1)
  self.assertEqual(x["verified_transactions"],0)
 def test_settlement_claim_still_requires_authentication(self):
  x=classify_sales_observations([{**R,"record_type":"SETTLEMENT_RECEIPT"}],as_of="2026-10-25T10:00:00Z")
  self.assertFalse(x["learning_eligible"])
 def test_future_evidence_rejected(self):
  with self.assertRaises(ValueError):classify_sales_observations([R],as_of="2026-10-24T10:00:00Z")
 def test_duplicate_rejected(self):
  with self.assertRaises(ValueError):classify_sales_observations([R,R],as_of="2026-10-25T10:00:00Z")
 def test_nan_refused(self):
  with self.assertRaises(ValueError):classify_sales_observations([{**R,"amount_eur":"NaN"}],as_of="2026-10-25T10:00:00Z")
if __name__=="__main__":unittest.main()
