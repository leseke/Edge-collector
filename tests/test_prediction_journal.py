import tempfile
import unittest
from pathlib import Path
from intelligence.prediction_journal import create_prediction,append_outcome,_records
ARGS=dict(product_key="test-item",thesis="demand growth",rival="attention only",as_of="2026-10-25T08:00:00Z",evidence_ids=["src-a"],horizon_days=30,criterion="price median up")
class PredictionTests(unittest.TestCase):
 def test_horizons_and_idempotent_creation(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"log.jsonl";a=create_prediction(p,**ARGS);b=create_prediction(p,**ARGS)
   self.assertEqual(a["id"],b["id"]);self.assertEqual(len(_records(p)),1)
   self.assertEqual(a["due_at"],"2026-11-24T08:00:00+00:00")
 def test_no_early_outcome(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"log.jsonl";a=create_prediction(p,**ARGS)
   with self.assertRaises(ValueError):append_outcome(p,prediction_id=a["id"],observed_at="2026-11-01T00:00:00Z",outcome="POSITIVE",evidence_ids=["new"],note="too early")
 def test_append_only_outcome(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"log.jsonl";a=create_prediction(p,**ARGS)
   append_outcome(p,prediction_id=a["id"],observed_at="2026-11-25T00:00:00Z",outcome="INCONCLUSIVE",evidence_ids=["new"],note="mixed result")
   self.assertEqual(len(_records(p)),2)
   with self.assertRaises(ValueError):append_outcome(p,prediction_id=a["id"],observed_at="2026-11-26T00:00:00Z",outcome="POSITIVE",evidence_ids=["new"],note="rewrite")
 def test_reject_no_evidence(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):create_prediction(Path(d)/"a",**{**ARGS,"evidence_ids":[]})
 def test_no_purchase_decision(self):
  with tempfile.TemporaryDirectory() as d:
   a=create_prediction(Path(d)/"a",**ARGS)
   self.assertFalse(a["execution_authorized"]);self.assertEqual(a["decision"],"NOT_EVALUATED")
if __name__=="__main__":unittest.main()
