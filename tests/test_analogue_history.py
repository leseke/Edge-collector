import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import analogue_history as m
from test_commercial_reaction_history import fixture, row


def episode(key, product, day):
    stamp = f'2026-10-{day:02d}T18:00:00Z'
    return dict(id=key, product_id=product, observation_id=product, source_url='https://example.com/' + product,
                seller='LDLC', currency='EUR', family='OBSERVED_STOCKOUT', detected_price='12.95',
                occurrence_interval_end=stamp, windows=[dict(horizon_hours=h, status='MEASURED',
                observed_at=f'2026-10-{day+1:02d}T18:00:00Z', availability='IN_STOCK') for h in (24, 72, 168)])


def reports_for(events):
    rows = []
    for e in events:
        day = int(e['occurrence_interval_end'][8:10])
        rows.append(row(f'2026-10-{day:02d}T06:00:00Z', id=e['observation_id'], product_id=e['product_id'],
                        url=e['source_url'], sha=e['id']))
    return [dict(observations=rows)]


class AnalogueTests(unittest.TestCase):
    def test_feature_freeze_ignores_future_price(self):
        e, reports = fixture()
        event = m.follow([e], reports, '2026-10-31T00:00:00Z')['events'][0]
        before = m.configuration(event, reports)
        reports.append(dict(observations=[row('2026-10-30T18:00:00Z', price='99999')]))
        self.assertEqual(before, m.configuration(event, reports))
        self.assertEqual(before['prior_price_change_pct'], 0)

    def test_self_cannot_be_its_own_precedent(self):
        e = episode('one', 'p1', 10)
        result = m.retrieve(dict(events=[e, e], observed_at='2026-10-31T00:00:00Z'), reports_for([e]))
        self.assertEqual(result['verified_episode_count'], 1)
        self.assertEqual(result['queries'][0]['horizons'][0]['sample_count'], 0)

    def test_outcome_after_signal_is_excluded_even_if_known_today(self):
        a, q = episode('a', 'pa', 10), episode('q', 'pq', 11)
        a['windows'][0]['observed_at'] = '2026-10-12T18:00:00Z'
        r = m.retrieve(dict(events=[a, q], observed_at='2026-10-31T00:00:00Z'), reports_for([a,q]))
        h = r['queries'][1]['horizons'][0]
        self.assertEqual(h['sample_count'], 0)
        self.assertIn('OUTCOME_NOT_KNOWN_AT_QUERY_TIME', [e['reason'] for e in h['exclusions']])

    def test_mature_prior_episode_is_selected_with_evidence(self):
        a, q = episode('a', 'pa', 10), episode('q', 'pq', 15)
        r = m.retrieve(dict(events=[a,q], observed_at='2026-10-31T00:00:00Z'), reports_for([a,q]))
        h = r['queries'][1]['horizons'][0]
        self.assertEqual(h['sample_count'], 1)
        self.assertIsNone(h['estimated_in_stock_frequency'])
        self.assertEqual(h['analogues'][0]['configuration']['evidence'][0]['body_sha256'], 'a')
        self.assertEqual(h['analogues'][0]['similarity']['score'], 1)

    def test_same_product_cannot_inflate_samples(self):
        a,b,q = episode('a','pa',5), episode('b','pa',8), episode('q','pq',15)
        r=m.retrieve(dict(events=[a,b,q], observed_at='2026-10-31T00:00:00Z'), reports_for([a,b,q]))
        self.assertEqual(r['queries'][2]['horizons'][0]['sample_count'],1)

    def test_missing_prior_feature_is_not_imputed(self):
        a,q=episode('a','pa',5),episode('q','pq',15)
        r=m.retrieve(dict(events=[a,q], observed_at='2026-10-31T00:00:00Z'), reports_for([q]))
        self.assertEqual(r['queries'][1]['horizons'][0]['sample_count'],0)

    def test_currency_and_event_family_must_match(self):
        a,q=episode('a','pa',5),episode('q','pq',15); a['currency']='USD'
        r=m.retrieve(dict(events=[a,q], observed_at='2026-10-31T00:00:00Z'), reports_for([a,q]))
        self.assertEqual(r['queries'][1]['horizons'][0]['sample_count'],0)

    def test_only_sufficient_unique_products_yield_labelled_frequency(self):
        events=[episode(str(i),'p'+str(i),i+1) for i in range(5)] + [episode('q','pq',15)]
        r=m.retrieve(dict(events=events, observed_at='2026-10-31T00:00:00Z'), reports_for(events))
        h=r['queries'][-1]['horizons'][0]
        self.assertEqual(h['sample_count'],5)
        self.assertEqual(h['estimated_in_stock_frequency'],1)
        self.assertFalse(r['calibrated_for_future_prediction'])
        self.assertFalse(r['queries'][-1]['buy_signal'])


if __name__ == '__main__': unittest.main()
