import json
import tempfile
import unittest
from pathlib import Path
from tools.review_tcgdex_catalogue import main

class CatalogueCLITests(unittest.TestCase):
 def test_valid_snapshot(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"sets.json"
   p.write_text(json.dumps([{"id":"swsh1","name":"Épée et Bouclier"}]),encoding="utf-8")
   r=main(["--input",str(p),"--observed-at","2026-10-29T20:00:00Z"])
   self.assertEqual(r["set_count"],1)
   self.assertFalse(r["market_offer_evidence"])
 def test_empty_file_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"sets.json"
   p.write_text("[]",encoding="utf-8")
   with self.assertRaises(ValueError):main(["--input",str(p),"--observed-at","2026-10-29T20:00:00Z"])
 def test_missing_file_rejected(self):
  with self.assertRaises(ValueError):main(["--input","/does/not/exist/sets.json","--observed-at","2026-10-29T20:00:00Z"])
if __name__=="__main__":unittest.main()
