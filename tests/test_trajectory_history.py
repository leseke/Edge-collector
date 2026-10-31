import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]/'scripts'))
import trajectory_history as m


def series(code=40000, overrides=None, start='2019-01', count=48):
    overrides=overrides or {}
    first=m.month_index(start)
    return {'id':str(code), 'source_url':f'https://promoklocki.pl/lego-icons-{code}-fixture-h{code}',
        'points':[{'month':m.month_name(first+i),'price_pln':overrides.get(m.month_name(first+i),'100'),
                   'source_row':i+2} for i in range(count)]}


def query(episodes, code='40000', month='2021-06'):
    return next(e for e in episodes if e['configuration']['series_id']==code and e['configuration']['anchor_month']==month)


class TrajectoryTests(unittest.TestCase):
    def test_missing_month_interrupts_features(self):
        data=series(overrides={'2021-03':None})
        episodes=m.build_episodes([data])
        self.assertFalse(any(e['configuration']['anchor_month']=='2021-06' for e in episodes))
        self.assertTrue(any(e['configuration']['anchor_month']=='2021-07' for e in episodes))

    def test_intermediate_missing_month_invalidates_horizon(self):
        e=m.build_episodes([series(overrides={'2021-08':None})])
        q=query(e)
        self.assertIn(1,q['outcomes'])
        self.assertNotIn(3,q['outcomes'])
        self.assertNotIn(12,q['outcomes'])

    def test_future_outcome_changes_cannot_change_query_features_or_estimate(self):
        data=[series(i) for i in range(40000,40012)]
        e=m.build_episodes(data);q=query(e)
        before=m.predict(q['configuration'],e)
        changed=copy.deepcopy(data)
        for s in changed:
            for p in s['points']:
                if p['month']>'2021-06':p['price_pln']='9999'
        later=m.build_episodes(changed);q2=query(later)
        self.assertEqual(q['configuration'],q2['configuration'])
        self.assertEqual(before,m.predict(q2['configuration'],later))

    def test_every_precedent_outcome_strictly_before_query(self):
        e=m.build_episodes([series(i) for i in range(40000,40012)])
        q=query(e)['configuration']
        p=m.predict(q,e)
        self.assertTrue(any(r['sample_count'] for r in p))
        for h in p:
            for matched in h['matches']:
                self.assertLess(matched['outcome']['target_index'],q['anchor_index'])
                self.assertNotEqual(matched['configuration']['product_group_hint'],q['product_group_hint'])

    def test_same_reference_hint_does_not_add_independent_trials(self):
        a=series(40000);b=series(40000);b['id']='alias';b['source_url']+='-alias'
        # Different URL but same numeric reference hint must still be excluded.
        e=m.build_episodes([a,b]);q=query(e)['configuration']
        self.assertTrue(all(p['sample_count']==0 for p in m.predict(q,e)))

    def test_only_one_episode_per_reference_retained(self):
        e=m.build_episodes([series(40000),series(40001)])
        p=m.predict(query(e)['configuration'],e)
        self.assertTrue(all(h['sample_count']==1 for h in p))
        self.assertTrue(all(h['estimated_positive_change_frequency'] is None for h in p))

    def test_sufficient_sample_is_explicitly_computed(self):
        e=m.build_episodes([series(i) for i in range(40000,40012)])
        p=m.predict(query(e)['configuration'],e)[0]
        self.assertEqual(p['sample_count'],11)
        self.assertEqual(p['estimated_positive_change_frequency'],0)
        self.assertEqual(p['estimated_median_change_pct'],0)
        self.assertFalse(p['buy_signal'])

    def test_query_sampling_ignores_held_out_outcomes(self):
        e=m.build_episodes([series(i) for i in range(40000,40025)])
        expected=[q['configuration']['id'] for q in m.choose_queries(e)]
        for q in e:q['outcomes']={}
        self.assertEqual(expected,[q['configuration']['id'] for q in m.choose_queries(e)])

    def test_simple_baseline_and_false_positive_metrics_use_same_queries(self):
        p={'horizon_months':1,'status':'COMPUTED_RETROSPECTIVE_ESTIMATE',
           'estimated_positive_change_frequency':.8,'baseline_positive_change_frequency':.2,
           'estimated_median_change_pct':10,'baseline_median_change_pct':0,
           'actual_outcome':{'change_pct':-5}}
        missing=copy.deepcopy(p);missing['actual_outcome']=None
        r=m.metrics([{'predictions':[p,missing]}])[0]
        self.assertEqual(r['paired_evaluations'],1)
        self.assertEqual(r['false_positive'],1)
        self.assertEqual(r['unmeasured_query_outcomes'],1)
        self.assertAlmostEqual(r['brier_score'],.64)
        self.assertAlmostEqual(r['baseline_prior_frequency_brier'],.04)
        self.assertEqual(r['mean_absolute_error_pct_points'],15)
        self.assertEqual(r['no_change_baseline_mae_pct_points'],5)
        self.assertEqual(r['direction_accuracy'],0)
        self.assertEqual(r['baseline_direction_accuracy'],1)
        self.assertFalse(r['predictive_advantage_established'])

    def test_remote_season_and_price_levels_do_not_force_matches(self):
        e=m.build_episodes([series(40000),series(40001)])
        a=query(e)['configuration'];b=copy.deepcopy(a)
        b['anchor_index']-=6
        self.assertIsNone(m.distance(a,b))
        b=copy.deepcopy(a);b['price_pln']=10000
        self.assertIsNone(m.distance(a,b))

    def test_duplicate_or_nonfinite_normalized_evidence_rejected(self):
        with self.assertRaises(ValueError):m.build_episodes([series(),series()])
        with self.assertRaises(ValueError):m.build_episodes([series(overrides={'2021-03':'NaN'})])


if __name__=='__main__':unittest.main()
