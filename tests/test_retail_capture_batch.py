import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from intelligence.retail_capture_batch import import_capture_batch

B=b"Public product listing source bytes for authorized research testing"
def capture(ident="sku",digest=None):
 return {"source_id":"store","source_domain":"example.org","listing_url":"https://example.org/item",
  "actual_seller":"Store","product_key":ident,"vertical":"TCG","offer_state":"UNKNOWN",
  "observed_at":"2026-10-28T12:00:00Z","price_eur":None,
  "source_snapshot_sha256":digest or hashlib.sha256(B).hexdigest()}
def prepare(directory,entries):
 p=Path(directory)
 (p/"capture.html").write_bytes(B)
 (p/"manifest.json").write_text(json.dumps(entries),encoding="utf-8")
 return p/"manifest.json",p/"journal.jsonl"

class BatchTests(unittest.TestCase):
 def test_import_and_duplicate(self):
  with tempfile.TemporaryDirectory() as d:
   m,j=prepare(d,[{"capture":capture(),"snapshot_file":"capture.html"}])
   self.assertEqual(import_capture_batch(manifest_path=m,journal_path=j,as_of="2026-10-28T13:00:00Z")["new_observations"],1)
   self.assertEqual(import_capture_batch(manifest_path=m,journal_path=j,as_of="2026-10-28T13:00:00Z")["duplicates"],1)
   self.assertEqual(len(j.read_text().splitlines()),1)
 def test_bad_second_entry_no_partial_journal(self):
  with tempfile.TemporaryDirectory() as d:
   m,j=prepare(d,[{"capture":capture(),"snapshot_file":"capture.html"},{"capture":capture("bad","a"*64),"snapshot_file":"capture.html"}])
   with self.assertRaises(ValueError):import_capture_batch(manifest_path=m,journal_path=j,as_of="2026-10-28T13:00:00Z")
   self.assertFalse(j.exists())
 def test_path_traversal_denied(self):
  with tempfile.TemporaryDirectory() as d:
   m,j=prepare(d,[{"capture":capture(),"snapshot_file":"../secret"}])
   with self.assertRaises(ValueError):import_capture_batch(manifest_path=m,journal_path=j,as_of="2026-10-28T13:00:00Z")
   self.assertFalse(j.exists())
if __name__=="__main__":unittest.main()
