import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from tools.import_retail_captures import main

S=b"Retail capture fixture bytes for deterministic local import only"
def fixture(folder):
    folder=Path(folder)
    (folder/"item.html").write_bytes(S)
    row={"source_id":"shop","source_domain":"example.org",
         "listing_url":"https://example.org/item","actual_seller":"Shop",
         "product_key":"pokemon-sealed-fr","vertical":"TCG",
         "offer_state":"UNKNOWN","observed_at":"2026-10-28T12:00:00Z",
         "price_eur":"39.90","source_snapshot_sha256":hashlib.sha256(S).hexdigest()}
    (folder/"manifest.json").write_text(json.dumps([{"capture":row,"snapshot_file":"item.html"}]))
    return folder/"manifest.json",folder/"history.jsonl"

class CLIIntegrationTests(unittest.TestCase):
    def test_import_and_replay(self):
        with tempfile.TemporaryDirectory() as d:
            manifest,journal=fixture(d)
            cmd=["--manifest",str(manifest),"--journal",str(journal),"--as-of","2026-10-28T13:00:00Z"]
            first=main(cmd)
            second=main(cmd)
            self.assertEqual(first["import"]["new_observations"],1)
            self.assertEqual(second["import"]["duplicates"],1)
            self.assertEqual(first["tracked_offers"],1)
            self.assertEqual(first["network_calls"],0)
    def test_future_capture_fails(self):
        with tempfile.TemporaryDirectory() as d:
            manifest,journal=fixture(d)
            with self.assertRaises(ValueError):
                main(["--manifest",str(manifest),"--journal",str(journal),"--as-of","2026-10-28T11:00:00Z"])
            self.assertFalse(journal.exists())
if __name__=="__main__":unittest.main()
