import json
import tempfile
import unittest
from pathlib import Path
from intelligence.public_mri_export import export_public

CASE={"case_id":"pk-cn-2022","label":"Pokémon Chine — 2022","as_of":"2022-09-21T23:59:59+08:00",
      "state":"RESEARCH_ONLY","thesis":"Community could persist","rival":"Attention could be transient",
      "limitations":"Publication dated; no contemporaneous capture.","source_urls":["https://www.pokemon.cn/tcg/product/16380.html"]}

class PublicMriExportTests(unittest.TestCase):
    def test_valid_json(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"public"/"mri.json"
            export_public([CASE],p)
            payload=json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(payload["cases"][0]["state"],"RESEARCH_ONLY")
    def test_disallow_capital(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                export_public([{**CASE,"capital":300}],Path(td)/"x.json")
    def test_disallow_decision(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                export_public([{**CASE,"decision":"BUY"}],Path(td)/"x.json")
    def test_require_timezone(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                export_public([{**CASE,"as_of":"2022-09-21T23:59:59"}],Path(td)/"x.json")
    def test_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                export_public([CASE,CASE],Path(td)/"x.json")
    def test_reject_non_https(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                export_public([{**CASE,"source_urls":["javascript:alert(1)"]}],Path(td)/"x.json")
if __name__=="__main__": unittest.main()
