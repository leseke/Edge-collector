import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import collection_guard as m

AT='2026-11-01T12:00:00Z'

class CollectionGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.report={'schema':'edge.commercial.snapshot.v1','observed_at':'2026-11-01T11:00:00Z','status':'PARTIAL',
            'observations':[dict(status='OK',price_kind='ASKING_PRICE',currency='EUR',price='100',
            observed_at='2026-11-01T11:00:00Z',body_sha256='proof')]}
        self.save()

    def save(self):
        raw=json.dumps(self.report).encode();path=self.root/'snapshots/123-1/report.json'
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        self.pointer=dict(schema='edge.public.live_capture.v1',snapshot_id='123-1',
            observed_at=self.report['observed_at'],status=self.report['status'],
            files={'report.json':dict(path='snapshots/123-1/report.json',sha256=hashlib.sha256(raw).hexdigest())})
        self.save_pointer()

    def save_pointer(self):
        (self.root/'latest.json').write_text(json.dumps(self.pointer))

    def test_hourly_wakeup_skips_verified_recent_capture(self):
        r=m.decision(self.root,'schedule',AT)
        self.assertFalse(r['collect']);self.assertEqual(r['reason'],'VERIFIED_CAPTURE_STILL_RECENT')

    def test_three_hour_boundary_collects(self):
        self.assertTrue(m.decision(self.root,'schedule','2026-11-01T14:00:00Z')['collect'])
        self.assertFalse(m.decision(self.root,'schedule','2026-11-01T13:59:59Z')['collect'])

    def test_push_and_manual_still_collect(self):
        for event in ['push','workflow_dispatch']:
            self.assertTrue(m.decision(self.root,event,AT)['collect'])

    def test_failed_capture_retries_even_when_recent(self):
        self.report['status']='FAILED';self.save()
        self.assertTrue(m.decision(self.root,'schedule',AT)['collect'])

    def test_cards_only_or_invalid_retail_proof_do_not_suppress_collection(self):
        for update in [{'price_kind':'AGGREGATED_INDICATIVE_LOW'},{'body_sha256':None},{'price':'NaN'},
                       {'status':'FAILED'},{'observed_at':'2026-11-01T13:00:00Z'}]:
            original=self.report['observations'][0].copy()
            self.report['observations'][0].update(update);self.save()
            self.assertTrue(m.decision(self.root,'schedule',AT)['collect'])
            self.report['observations'][0]=original

    def test_corrupt_missing_or_future_pointer_cannot_suppress_collection(self):
        self.pointer['files']['report.json']['sha256']='tampered';self.save_pointer()
        self.assertTrue(m.decision(self.root,'schedule',AT)['collect'])
        (self.root/'latest.json').unlink()
        self.assertTrue(m.decision(self.root,'schedule',AT)['collect'])
        self.report['observed_at']='2026-11-01T13:00:00Z';self.save()
        self.assertTrue(m.decision(self.root,'schedule',AT)['collect'])

    def test_pointer_cannot_escape_snapshot_directory(self):
        self.pointer['files']['report.json']['path']='../../elsewhere';self.save_pointer()
        self.assertTrue(m.decision(self.root,'schedule',AT)['collect'])

    def test_trigger_context_never_promotes_push_to_schedule(self):
        r=m.trigger_context({'GITHUB_EVENT_NAME':'push','GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1'})
        self.assertEqual(r['event'],'push');self.assertFalse(r['schedule_is_delivery_guarantee'])
        self.assertEqual(r['run_id'],'123')
        self.assertIsNone(m.trigger_context({'GITHUB_RUN_ID':'bad\nvalue'})['run_id'])
        self.assertEqual(m.trigger_context({})['event'],'local')

if __name__=='__main__':unittest.main()
