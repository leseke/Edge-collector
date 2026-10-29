import tempfile
import hashlib
import unittest
from pathlib import Path
from intelligence.retail_capture_import import import_reviewed_capture
from intelligence.retail_observation_history import summarize_retail_history
SNAPSHOT=b"Public retail listing document captured for research, not an authenticated sale"
BASE={"source_id":"example-store","source_domain":"example.org",
"listing_url":"https://example.org/item/123","actual_seller":"Example Store",
"product_key":"pokemon-fr-sealed-123","vertical":"TCG","offer_state":"IN_STOCK",
"observed_at":"2026-10-28T11:00:00Z","price_eur":"49.90",
"source_snapshot_sha256":hashlib.sha256(SNAPSHOT).hexdigest()}
class CaptureImportTests(unittest.TestCase):
 def test_capture_import_and_dedup(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"capture.jsonl"
   first=import_reviewed_capture(journal_path=p,capture=BASE,as_of="2026-10-28T12:00:00Z",snapshot_bytes=SNAPSHOT)
   second=import_reviewed_capture(journal_path=p,capture=BASE,as_of="2026-10-28T12:00:00Z",snapshot_bytes=SNAPSHOT)
   self.assertTrue(first["appended"])
   self.assertFalse(second["appended"])
   self.assertFalse(first["source_stock_verified"])
   self.assertEqual(summarize_retail_history(p,as_of="2026-10-28T12:00:00Z")["observations"],1)
 def test_future_record_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):
    import_reviewed_capture(journal_path=Path(d)/"capture.jsonl",capture=BASE,as_of="2026-10-28T10:00:00Z",snapshot_bytes=SNAPSHOT)
 def test_invalid_hash_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):
    import_reviewed_capture(journal_path=Path(d)/"capture.jsonl",capture={**BASE,"source_snapshot_sha256":"bad"},as_of="2026-10-28T12:00:00Z",snapshot_bytes=SNAPSHOT)
 def test_tampered_snapshot_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):
    import_reviewed_capture(journal_path=Path(d)/"capture.jsonl",capture=BASE,as_of="2026-10-28T12:00:00Z",snapshot_bytes=SNAPSHOT+b"!")
 def test_domain_spoof_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):
    import_reviewed_capture(journal_path=Path(d)/"capture.jsonl",capture={**BASE,"listing_url":"https://example.org.malicious.net/item"},as_of="2026-10-28T12:00:00Z",snapshot_bytes=SNAPSHOT)
if __name__=="__main__":unittest.main()
