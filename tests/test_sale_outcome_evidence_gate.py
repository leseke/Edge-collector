import unittest
from intelligence.sale_outcome_evidence_gate import examine_sale_evidence
P={"type":"PREDICTION","id":"p1","product_key":"card","due_at":"2026-02-01T00:00:00Z"}
O={"type":"OUTCOME","prediction_id":"p1","outcome":"POSITIVE","observed_at":"2026-02-02T00:00:00Z","evidence_ids":["sale1"]}
S={"evidence_id":"sale1","source_url":"https://example.org/sale","product_key":"card","sold_at":"2026-02-01T09:00:00Z","sale_price_eur":50,"independently_verified":True}
def review(sales):return examine_sale_evidence(prediction=P,outcome=O,observations=sales,as_of="2026-02-03T00:00:00Z")
class SaleGateTests(unittest.TestCase):
 def test_claim_of_verification_does_not_prove_outcome(self):
  x=review([S]);self.assertFalse(x["market_outcome_proven"]);self.assertFalse(x["eligible_for_learning"])
 def test_no_records_not_verified(self):
  self.assertEqual(review([])["status"],"NEEDS_INDEPENDENT_AUDIT")
 def test_future_observation_refused(self):
  with self.assertRaises(ValueError):review([{**S,"sold_at":"2026-02-04T00:00:00Z"}])
 def test_wrong_product_not_corroborrated(self):
  self.assertFalse(review([{**S,"product_key":"wrong"}])["corroborated"])
 def test_duplicates_rejected(self):
  with self.assertRaises(ValueError):review([S,S])
if __name__=="__main__":unittest.main()
