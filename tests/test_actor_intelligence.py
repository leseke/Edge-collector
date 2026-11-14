import unittest
from intelligence.actor_intelligence import build_actor_brief, propose_scenarios, validate_actor, validate_action

A={'actor_id':'brand-1','name':'Brand One','actor_type':'brand'}
E={'event_id':'ev1','actor_id':'brand-1','subject_id':'item1','action_type':'publication','occurred_at':'2026-10-01T10:00:00Z','observed_at':'2026-10-01T10:03:00Z','source_id':'src1','summary':'Announces an anniversary set'}
L={**E,'event_id':'late','observed_at':'2026-10-10T10:00:00Z'}

class TestActorIntelligence(unittest.TestCase):
    def test_time_cut(self):
        self.assertEqual(len(build_actor_brief(A,[E,L],as_of='2026-10-02T00:00:00Z')['known_actions']),1)
    def test_no_future_evidence(self):
        b=build_actor_brief(A,[E,L],as_of='2026-10-02T00:00:00Z')
        with self.assertRaises(ValueError):
            propose_scenarios(b,'demand_growth','attention_only',mechanism='M',supporting_event_ids=['late'],counter_event_ids=[],falsifiers=['no rise'],horizon_days=7)
    def test_scenarios_undecided(self):
        b=build_actor_brief(A,[E],as_of='2026-10-02T00:00:00Z')
        p=propose_scenarios(b,'demand_growth','attention_only',mechanism='Nostalgia exposure',supporting_event_ids=['ev1'],counter_event_ids=[],falsifiers=['No new purchasers'],horizon_days=14)
        self.assertEqual(p['policy_decision'],'NOT_EVALUATED')
        self.assertEqual(p['causality'],'not_established')
    def test_missing_rival_rejected(self):
        b=build_actor_brief(A,[E],as_of='2026-10-02T00:00:00Z')
        with self.assertRaises(ValueError):
            propose_scenarios(b,'demand_growth','demand_growth',mechanism='X',supporting_event_ids=[],counter_event_ids=[],falsifiers=['X'],horizon_days=2)
    def test_sensitive_profile_rejected(self):
        with self.assertRaises(ValueError):
            validate_actor({**A,'private_contact':'secret'})
    def test_finance_rejected(self):
        with self.assertRaises(ValueError):
            validate_action({**E,'allocation':50})
    def test_missing_source_rejected(self):
        with self.assertRaises(ValueError):
            validate_action({**E,'source_id':''})
    def test_reproducible_id(self):
        b=build_actor_brief(A,[E],as_of='2026-10-02T00:00:00Z')
        kw=dict(mechanism='X',supporting_event_ids=['ev1'],counter_event_ids=[],falsifiers=['No price change'],horizon_days=7)
        self.assertEqual(propose_scenarios(b,'demand_growth','attention_only',**kw)['hypothesis_id'],propose_scenarios(b,'demand_growth','attention_only',**kw)['hypothesis_id'])

if __name__=='__main__':
    unittest.main()
