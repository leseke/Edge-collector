import tempfile
import unittest
from pathlib import Path
from intelligence.prediction_journal import create_prediction
from intelligence.learning_commitment_ledger import seal_forecast,verified_commitments
class LedgerTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.addCleanup(self.temp.cleanup)
  self.path=Path(self.temp.name)/"commitments.jsonl"
  self.pred=create_prediction(Path(self.temp.name)/"journal.jsonl",product_key="item",thesis="rise",rival="stable",as_of="2026-01-01T00:00:00Z",evidence_ids=["e1"],horizon_days=30,criterion="median price increases")
  self.kw=dict(prediction=self.pred,baseline_positive=False,challenger_positive=True,committed_at="2026-01-01T00:00:00Z",evidence_hashes={"e1":"a"*64})
 def test_seal_is_idempotent(self):
  a=seal_forecast(self.path,**self.kw)
  self.assertEqual(seal_forecast(self.path,**self.kw),a)
  self.assertEqual(len(verified_commitments(self.path,{self.pred["id"]:self.pred})),1)
 def test_late_commitment_denied(self):
  with self.assertRaises(ValueError):seal_forecast(self.path,**{**self.kw,"committed_at":"2026-01-02T00:00:00Z"})
 def test_change_is_denied(self):
  seal_forecast(self.path,**self.kw)
  with self.assertRaises(ValueError):seal_forecast(self.path,**{**self.kw,"challenger_positive":False})
 def test_tamper_detected(self):
  seal_forecast(self.path,**self.kw)
  self.path.write_text(self.path.read_text().replace('"baseline_positive":false','"baseline_positive":true'))
  with self.assertRaises(ValueError):verified_commitments(self.path,{self.pred["id"]:self.pred})
 def test_unmatched_evidence_rejected(self):
  with self.assertRaises(ValueError):seal_forecast(self.path,**{**self.kw,"evidence_hashes":{"other":"a"*64}})
if __name__=="__main__":unittest.main()
