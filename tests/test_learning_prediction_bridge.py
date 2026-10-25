import tempfile
import unittest
from pathlib import Path
from intelligence.prediction_journal import create_prediction,append_outcome
from intelligence.learning_prediction_bridge import evaluate_journal

class BridgeTests(unittest.TestCase):
 def seed(self,path,n,positive=True):
  forecasts=[]
  for i in range(n):
   a=create_prediction(path,product_key=f"product-{i}",thesis="growth",rival="stable",as_of="2026-01-01T00:00:00Z",evidence_ids=[f"source-{i}"],horizon_days=30,criterion="higher prices")
   append_outcome(path,prediction_id=a["id"],observed_at="2026-02-01T00:00:00Z",outcome="POSITIVE" if positive else "NEGATIVE",evidence_ids=[f"result-{i}"],note="assessor supplied outcome")
   forecasts.append({"prediction_id":a["id"],"forecast_at":"2026-01-01T00:00:00Z","baseline_positive":False,"challenger_positive":True})
  return forecasts
 def test_30_pairs_do_not_enable_promotion(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"journal.jsonl";items=self.seed(p,30)
   report=evaluate_journal(p,items,as_of="2026-02-02T00:00:00Z")
   self.assertEqual(report["status"],"REVIEW_REQUIRED")
   self.assertEqual(report["cases"],30)
   self.assertFalse(report["outcome_provenance_verified"])
   self.assertFalse(report["promotion_authorized"])
 def test_no_lookahead(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"j";items=self.seed(p,1)
   report=evaluate_journal(p,items,as_of="2026-01-15T00:00:00Z")
   self.assertEqual(report["cases"],0)
   self.assertEqual(report["exclusions"]["PENDING"],1)
 def test_late_forecast_refused(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"j";items=self.seed(p,1)
   items[0]["forecast_at"]="2026-01-02T00:00:00Z"
   with self.assertRaises(ValueError):evaluate_journal(p,items,as_of="2026-02-02T00:00:00Z")
 def test_duplicate_commitment_refused(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"j";items=self.seed(p,1)
   with self.assertRaises(ValueError):evaluate_journal(p,items+items,as_of="2026-02-02T00:00:00Z")
if __name__=="__main__":unittest.main()
