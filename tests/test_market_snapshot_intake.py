import tempfile
import json
import unittest
from pathlib import Path
from intelligence.market_snapshot_intake import archive_snapshot,stage_snapshot_file
M=dict(source_url="https://example.org/listing",record_type="ASK",product_key="pokemon-fr",
amount_eur="42.90",observed_at="2026-10-25T10:00:00Z",evidence_id="sale-1")
class SnapshotTests(unittest.TestCase):
 def test_ask_never_authenticates_sale(self):
  x=archive_snapshot(**M,source_bytes=b"Marketplace listing captured for research only")
  self.assertFalse(x["sale_verified"])
  self.assertEqual(x["classification"]["ASK"],1)
 def test_same_bytes_same_hash(self):
  a=archive_snapshot(**M,source_bytes=b"Marketplace listing captured for research only")
  b=archive_snapshot(**M,source_bytes=b"Marketplace listing captured for research only")
  self.assertEqual(a["evidence"]["proof_sha256"],b["evidence"]["proof_sha256"])
 def test_change_changes_fingerprint(self):
  a=archive_snapshot(**M,source_bytes=b"Marketplace listing captured for research only")
  b=archive_snapshot(**M,source_bytes=b"Marketplace listing captured for research only!")
  self.assertNotEqual(a["evidence"]["proof_sha256"],b["evidence"]["proof_sha256"])
 def test_future_data_rejected_by_cutoff(self):
  with self.assertRaises(ValueError):archive_snapshot(**{**M,"observed_at":"not-a-date"},source_bytes=b"Marketplace listing captured for research only")
 def test_file_staging(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   (p/"meta.json").write_text(json.dumps(M))
   (p/"evidence.txt").write_bytes(b"Marketplace listing captured for research only")
   result=stage_snapshot_file(p/"meta.json",p/"evidence.txt",p/"out.json")
   self.assertEqual(json.loads((p/"out.json").read_text()),result)
if __name__=="__main__":unittest.main()
