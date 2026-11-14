import unittest
from intelligence.market_reaction import snapshot, make_hypothesis, event_window, assess_prediction, validate_measure

E={'id':'e1','actor':'brand','kind':'publication','occurred_at':'2026-09-10T12:00:00Z','observed_at':'2026-09-10T12:30:00Z','source_id':'source-a','summary':'Annonce publique','subject_id':'pokemon-sc'}

def m(i,at,seen,value,metric='mentions',kind=None):
    v={'id':i,'subject_id':'pokemon-sc','metric':metric,'value':value,'measured_at':at,'observed_at':seen,'source_id':'source-b','method':'manual_import'}
    if kind: v['evidence_kind']=kind
    return v

MEAS=[m('before','2026-09-09T12:00:00Z','2026-09-09T13:00:00Z',10),m('after','2026-09-11T12:00:00Z','2026-09-11T13:00:00Z',30),m('late-discovery','2026-09-09T16:00:00Z','2026-09-20T13:00:00Z',999)]

class MarketReactionTests(unittest.TestCase):
    def test_future_information_does_not_leak(self):
        s=snapshot([E],MEAS,'2026-09-12T00:00:00Z')
        self.assertEqual([x['id'] for x in s['measures']],['before','after'])
    def test_late_discovery_does_not_rewrite_backtest(self):
        w=event_window(E,MEAS,'2026-09-12T00:00:00Z','mentions')
        self.assertEqual(w['delta_median'],20)
        self.assertEqual(w['causality'],'not_established')
    def test_no_data_not_invented(self):
        w=event_window(E,[], '2026-09-30T00:00:00Z','mentions')
        self.assertIsNone(w['delta_median'])
    def test_two_rival_hypotheses(self):
        h=make_hypothesis(E,'Nouveaux acheteurs','Effet temporaire sans achats',[{'metric':'mentions','direction':'increase','by_days':7}], 'Engagement en baisse', 'Risque de faux signal')
        self.assertEqual(h['policy_decision'],'NOT_EVALUATED')
        self.assertTrue(h['rival_explanation'])
    def test_pending_future_prediction(self):
        h=make_hypothesis(E,'Intérêt','Bruit',[{'metric':'mentions','direction':'increase','by_days':7}],'Stagnation','Biais')
        self.assertEqual(assess_prediction(h,E,MEAS,'2026-09-12T00:00:00Z')['outcomes'][0]['result'],'PENDING')
        self.assertEqual(assess_prediction(h,E,MEAS,'2026-09-18T00:00:00Z')['outcomes'][0]['result'],'SUPPORTED')
    def test_no_false_sold_transaction(self):
        with self.assertRaises(ValueError): validate_measure(m('x','2026-09-11T12:00:00Z','2026-09-11T13:00:00Z',8,'sold_count'))
    def test_no_financial_action(self):
        with self.assertRaises(ValueError): snapshot([{**E,'decision':'BUY'}],[],'2026-09-20T00:00:00Z')
    def test_timezone_required(self):
        with self.assertRaises(ValueError): snapshot([{**E,'occurred_at':'2026-09-10T12:00:00'}],[],'2026-09-20T00:00:00Z')
    def test_ambiguity_not_faked(self):
        h=make_hypothesis(E,'Demande','Promotion artificielle',[{'metric':'sold_count','direction':'increase','by_days':7}],'Aucune transaction','Très faible liquidité')
        self.assertEqual(assess_prediction(h,E,MEAS,'2026-09-20T00:00:00Z')['outcomes'][0]['result'],'NO_DATA')

if __name__=='__main__': unittest.main()
