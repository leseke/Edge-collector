import unittest
from copy import deepcopy
from intelligence.blind_replay import freeze_case, evaluate_frozen

A={'actor_id':'brand1','name':'Brand','actor_type':'brand'}
ACT={'event_id':'ev1','actor_id':'brand1','subject_id':'card1','action_type':'publication','occurred_at':'2026-09-10T12:00:00Z','observed_at':'2026-09-10T12:05:00Z','source_id':'s1','summary':'public launch'}
EV={'id':'ev1','actor':'Brand','kind':'publication','occurred_at':'2026-09-10T12:00:00Z','observed_at':'2026-09-10T12:05:00Z','source_id':'s1','summary':'public launch','subject_id':'card1'}
def metric(i,t,seen,val):
    return {'id':i,'subject_id':'card1','metric':'mentions','value':val,
            'measured_at':t,'observed_at':seen,'source_id':'s2','method':'test_fixture'}
BEFORE=metric('before','2026-09-09T12:00:00Z','2026-09-09T13:00:00Z',10)
AFTER=metric('after','2026-09-11T12:00:00Z','2026-09-11T13:00:00Z',30)
LATE=metric('retro','2026-09-09T12:00:00Z','2026-09-20T13:00:00Z',999)

def freeze():
    return freeze_case(A,[ACT],[EV],[BEFORE,AFTER,LATE],
        as_of='2026-09-10T14:00:00Z',thesis='demand_growth',rival='attention_only',
        mechanism='new attention',supporting_event_ids=['ev1'],
        counter_event_ids=[],falsifiers=['No sustained interest'],horizon_days=7,
        prediction={'metric':'mentions','direction':'increase','by_days':7})

class BlindReplayTests(unittest.TestCase):
    def test_later_measurement_absent_from_frozen_case(self):
        f=freeze()
        self.assertEqual(f['known_measure_ids'],['before'])
        self.assertEqual(f['status'],'FROZEN_UNVERIFIED')
    def test_prediction_waits_until_maturity(self):
        f=freeze()
        result=evaluate_frozen(f,[BEFORE,AFTER,LATE],as_of='2026-09-11T00:00:00Z')
        self.assertEqual(result['outcomes'][0]['result'],'PENDING')
    def test_late_observation_not_backfilled(self):
        f=freeze()
        r=evaluate_frozen(f,[BEFORE,AFTER,LATE],as_of='2026-09-18T00:00:00Z')
        self.assertEqual(r['outcomes'][0]['result'],'SUPPORTED')
        self.assertEqual(r['outcomes'][0]['delta'],20)
        self.assertEqual(r['forecast_skill'],'not_established')
    def test_tampering_refused(self):
        f=freeze()
        f['hypothesis']['mechanism']='changed after outcome'
        with self.assertRaises(ValueError):
            evaluate_frozen(f,[BEFORE,AFTER],as_of='2026-09-20T00:00:00Z')
    def test_no_future_event_can_support_thesis(self):
        future={**ACT,'event_id':'future','observed_at':'2026-09-21T00:00:00Z'}
        with self.assertRaises(ValueError):
            freeze_case(A,[ACT,future],[EV],[BEFORE],as_of='2026-09-10T14:00:00Z',
                thesis='demand_growth',rival='attention_only',mechanism='x',
                supporting_event_ids=['future'],counter_event_ids=[],
                falsifiers=['no change'],horizon_days=7,
                prediction={'metric':'mentions','direction':'increase','by_days':7})
if __name__=='__main__': unittest.main()
