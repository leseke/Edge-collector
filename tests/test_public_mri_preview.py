"""Offline checks for the static MRI preview and its public dataset."""
import json
from pathlib import Path
import unittest
from intelligence.public_mri_export import PUBLIC_KEYS, STATES, export_public
import tempfile

ROOT = Path(__file__).resolve().parents[1]
class PublicPreviewTests(unittest.TestCase):
    def test_public_fixture_schema_and_allowlist(self):
        d=json.loads((ROOT/"preview/data/mri_public.json").read_text(encoding="utf-8"))
        self.assertEqual(d["schema"],"edge.mri.public.v1")
        self.assertEqual(len(d["cases"]),2)
        for case in d["cases"]:
            self.assertEqual(set(case),PUBLIC_KEYS)
            self.assertIn(case["state"],STATES)
            self.assertEqual(case["state"],"RESEARCH_ONLY")
    def test_export_roundtrip(self):
        d=json.loads((ROOT/"preview/data/mri_public.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"data.json"
            export_public(d["cases"],out)
            self.assertEqual(json.loads(out.read_text(encoding="utf-8")),d)
    def test_static_page_read_only(self):
        page=(ROOT/"preview/index.html").read_text(encoding="utf-8")
        self.assertIn('fetch("./data/mri_public.json"',page)
        self.assertIn("textContent",page)
        self.assertNotIn("innerHTML",page)
        self.assertNotIn("localStorage",page)
        self.assertNotIn("github_token",page.lower())
        self.assertNotIn("Authorization",page)
    def test_no_buy_decisions_in_examples(self):
        raw=(ROOT/"preview/data/mri_public.json").read_text(encoding="utf-8")
        self.assertNotIn('"allocation"',raw)
        self.assertNotIn('"capital"',raw)
        self.assertNotIn('"decision"',raw)
if __name__=="__main__": unittest.main()
