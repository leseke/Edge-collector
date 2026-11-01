import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import publish_capture as m


def fixture(root):
    manifest={}
    for name,schema in m.SCHEMAS.items():
        doc={'schema':schema}
        if name=='report.json':doc.update(status='PARTIAL',observed_at='2026-11-01T08:00:00Z')
        b=json.dumps(doc).encode();(root/name).write_bytes(b);manifest[name]=hashlib.sha256(b).hexdigest()
    (root/'manifest.json').write_text(json.dumps(manifest));return manifest

class PublishCaptureTests(unittest.TestCase):
    def test_pointer_is_bound_to_one_immutable_snapshot_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manifest=fixture(root);p=m.build_pointer(root,'123-1')
            self.assertEqual(p['status'],'PARTIAL')
            self.assertEqual(p['financial_decision'],'NOT_ESTABLISHED')
            for name,f in p['files'].items():
                self.assertEqual(f['path'],'snapshots/123-1/'+name)
                self.assertEqual(f['sha256'],manifest[name])

    def test_tampered_file_cannot_be_advertised_as_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fixture(root);(root/'mri_cases.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'integrity'):m.build_pointer(root,'123-1')

    def test_missing_file_cannot_be_advertised_as_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fixture(root);(root/'collection_coverage.json').unlink()
            with self.assertRaises(FileNotFoundError):m.build_pointer(root,'123-1')

    def test_unexpected_schema_is_rejected_even_with_a_matching_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manifest=fixture(root);b=b'{"schema":"untrusted"}'
            (root/'mri_cases.json').write_bytes(b);manifest['mri_cases.json']=hashlib.sha256(b).hexdigest()
            (root/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'schema'):m.build_pointer(root,'123-1')

    def test_invalid_snapshot_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fixture(root)
            for value in ('../123','123-1/other','123','NaN-1'):
                with self.assertRaises(ValueError):m.build_pointer(root,value)

if __name__=='__main__':unittest.main()
