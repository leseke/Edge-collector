import tempfile
import unittest
from pathlib import Path
from intelligence.prediction_journal import create_prediction,append_outcome
from intelligence.learning_commitment_ledger import seal_forecast
from intelligence.prospective_learning_gate import assess_prospective_learning

class IntegratedGateTests(unittest.TestCase):
 def test_claimed_success_never_becomes_verified_improvement(self):
  with tempfile.TemporaryDirectory() as d:
   journal=Path(d)/"journal.jsonl";ledger=Path(d)/"ledger.jsonl"
   p=create_prediction(journal,product_key="card",thesis="rise",rival="flat",
       as_of="2026-01-01T00:00:00Z",evidence_ids=["e1"],horizon_days=30,criterion="price rose")
   seal_forecast(ledger,prediction=p,baseline_positive=False,challenger_positive=True,
       committed_at="2026-01-01T00:00:00Z",evidence_hashes={"e1":"a"*64})
   append_outcome(journal,prediction_id=p["id"],observed_at="2026-02-02T00:00:00Z",
       outcome="POSITIVE",evidence_ids=["sale1"],note="claimed observed sale")
   sale={"evidence_id":"sale1","source_url":"https://example.org/sale","product_key":"card",
       "sold_at":"2026-02-02T00:00:00Z","sale_price_eur":99,"independently_verified":True}
   result=assess_prospective_learning(journal_path=journal,ledger_path=ledger,
       sale_observations={p["id"]:[sale]},as_of="2026-02-03T00:00:00Z",
       typed_sale_observations={p["id"]:[{"evidence_id":"ask-1","record_type":"ASK",
           "product_key":"card","source_url":"https://example.org/ask",
           "observed_at":"2026-02-02T00:00:00Z","amount_eur":"99.00",
           "proof_sha256":"b"*64}]})
   self.assertEqual(result["preliminary"]["cases"],1)
   self.assertEqual(result["verified_outcome_count"],0)
   self.assertEqual(result["typed_sales_review"][0]["source_types"]["ASK"],1)
   self.assertEqual(result["typed_sales_review"][0]["independently_verified_sales"],0)
   self.assertFalse(result["learning_improvement_demonstrated"])
   self.assertFalse(result["method_promotion_authorized"])
   self.assertEqual(result["status"],"EVIDENCE_PENDING")
if __name__=="__main__":unittest.main()
