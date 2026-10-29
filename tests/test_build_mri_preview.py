import json
import tempfile
import unittest
from pathlib import Path
from tools.build_mri_preview import generate, INPUT

class GeneratedPreviewTests(unittest.TestCase):
    def test_generate_and_preserve_research_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/"mri.json"
            generate(INPUT,dest)
            payload=json.loads(dest.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["cases"]),2)
            self.assertEqual({x["state"] for x in payload["cases"]},{"RESEARCH_ONLY"})
            self.assertTrue(all("capture contemporaine" in x["limitations"] for x in payload["cases"]))
    def test_reject_unknown_case(self):
        item=json.loads(INPUT.read_text(encoding="utf-8"))
        item["cases"][0]["case_id"]="unreviewed"
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/"input.json"
            src.write_text(json.dumps(item),encoding="utf-8")
            with self.assertRaises(ValueError):
                generate(src,Path(tmp)/"output.json")
    def test_reject_qualified_replay_as_research(self):
        item=json.loads(INPUT.read_text(encoding="utf-8"))
        s=item["cases"][0]["sources"][0]
        s.update({"support":"contemporaneous_archive",
                  "captured_at":"2022-09-21T12:00:00+08:00",
                  "capture_url":"https://example.org/independent-archive"})
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/"input.json"
            src.write_text(json.dumps(item),encoding="utf-8")
            with self.assertRaises(ValueError):
                generate(src,Path(tmp)/"output.json")
if __name__=="__main__":
    unittest.main()
