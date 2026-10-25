import json
import tempfile
import unittest
from pathlib import Path
from tools.prepare_mri_public_release import prepare

class PublicReleaseReviewTests(unittest.TestCase):
    def test_missing_public_version_requires_review(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            r=prepare(p/"out", p/"absent.json")
            self.assertTrue(r["changed"])
            self.assertEqual(r["status"],"REVIEW_REQUIRED")
            self.assertFalse(r["publication_performed"])
            self.assertFalse(r["purchase_authorized"])
            self.assertTrue((p/"out/mri_public.json").is_file())
    def test_same_content_is_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            first=prepare(p/"first",p/"absent")
            second=prepare(p/"second",p/"first/mri_public.json")
            self.assertFalse(second["changed"])
            self.assertEqual(second["status"],"UNCHANGED")
    def test_invalid_existing_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            old=p/"old.json"
            old.write_text(json.dumps({"schema":"unknown","cases":[]}))
            with self.assertRaises(ValueError):
                prepare(p/"out",old)
if __name__=="__main__": unittest.main()
