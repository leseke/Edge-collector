import tempfile
import unittest
from pathlib import Path
from intelligence.prediction_journal import create_prediction
from intelligence.learning_commitment_ledger import seal_forecast
from intelligence.external_witness import commitment_manifest,examine_receipt

class WitnessTests(unittest.TestCase):
 def make(self):
  self.d=tempfile.TemporaryDirectory();self.addCleanup(self.d.cleanup)
  p=create_prediction(Path(self.d.name)/"pred",product_key="sample",thesis="rise",rival="stable",
    as_of="2026-01-01T00:00:00Z",evidence_ids=["s1"],horizon_days=30,criterion="higher median")
  r=seal_forecast(Path(self.d.name)/"ledger",prediction=p,baseline_positive=False,challenger_positive=True,
    committed_at="2026-01-01T00:00:00Z",evidence_hashes={"s1":"a"*64})
  return r
 def test_manifest_is_deterministic(self):
  r=self.make();self.assertEqual(commitment_manifest([r]),commitment_manifest([r]))
 def test_fake_receipt_cannot_grant_verification(self):
  manifest=commitment_manifest([self.make()])
  receipt={"manifest_sha256":manifest["manifest_sha256"],"commit_sha":"a"*40,
    "commit_timestamp":"2026-01-01T00:00:00Z","external_verified":True}
  status=examine_receipt(manifest,receipt)
  self.assertFalse(status["external_timestamp_verified"])
  self.assertFalse(status["promotion_authorized"])
 def test_tampering_rejected(self):
  r=self.make();r["baseline_positive"]=True
  with self.assertRaises(ValueError):commitment_manifest([r])
 def test_wrong_receipt_rejected(self):
  manifest=commitment_manifest([self.make()])
  receipt={"manifest_sha256":"0"*64,"commit_sha":"a"*40,
    "commit_timestamp":"2026-01-01T00:00:00Z","external_verified":False}
  with self.assertRaises(ValueError):examine_receipt(manifest,receipt)
if __name__=="__main__":unittest.main()
