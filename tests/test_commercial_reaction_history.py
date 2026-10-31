import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import commercial_reaction_history as m


def row(stamp, availability='OUT_OF_STOCK', sha='after', **updates):
    r = dict(id='retail', product_id='lego_40744', seller='LDLC', url='https://www.ldlc.com/fiche/1.html',
             currency='EUR', price='12.95', price_kind='ASKING_PRICE', status='OK',
             observed_at=stamp, body_sha256=sha, availability=availability)
    r.update(updates);return r


def fixture():
    before = row('2026-10-29T12:00:00Z', 'IN_STOCK', 'before')
    after = row('2026-10-29T18:00:00Z')
    event = dict(id='event1', kind='AVAILABILITY_CHANGE', observation_id='retail', product_id='lego_40744',
                 seller='LDLC', source_url=after['url'], field='availability', before='IN_STOCK', after='OUT_OF_STOCK',
                 window_start=before['observed_at'], window_end=after['observed_at'],
                 previous_evidence_sha256='before', evidence_sha256='after')
    return event, [dict(observations=[before]), dict(observations=[after])]


class CommercialReactionTests(unittest.TestCase):
    def test_evidence_verified_stockout(self):
        e, reports = fixture();r = m.follow([e], reports, '2026-10-30T12:00:00Z')
        self.assertEqual(r['events'][0]['family'], 'OBSERVED_STOCKOUT')
        self.assertEqual(r['events'][0]['anchor_kind'], 'OBSERVATION_WINDOW_END_NOT_EXACT_EVENT_TIME')

    def test_replay_is_not_new_event(self):
        e, reports = fixture();r = m.follow([e, e, e], reports * 3, '2026-10-30T12:00:00Z')
        self.assertEqual(len(r['events']), 1)
        self.assertEqual(r['events'][0]['successful_captures_since_detection'], 1)

    def test_wrong_hash_rejected(self):
        e, reports = fixture();e['evidence_sha256'] = 'wrong'
        self.assertEqual(m.follow([e], reports, '2026-10-30T12:00:00Z')['events'], [])

    def test_wrong_seller_rejected(self):
        e, reports = fixture();reports[0]['observations'][0]['seller'] = 'Other'
        self.assertEqual(m.follow([e], reports, '2026-10-30T12:00:00Z')['events'], [])

    def test_event_value_must_match_actual_snapshot(self):
        e, reports = fixture();reports[0]['observations'][0]['availability'] = 'OUT_OF_STOCK'
        self.assertEqual(m.follow([e], reports, '2026-10-30T12:00:00Z')['events'], [])

    def test_indicative_index_not_retail_event(self):
        e, reports = fixture();e['kind'] = 'INDICATIVE_PRICE_CHANGE'
        result = m.follow([e], reports, '2026-10-30T12:00:00Z')
        self.assertEqual(result['events'], [])
        self.assertEqual(result['excluded_events'][0]['reason'], 'NOT_A_RETAIL_OFFER_TRANSITION')

    def test_early_capture_does_not_measure_future_horizon(self):
        e, reports = fixture();reports.append(dict(observations=[row('2026-10-30T12:00:00Z', 'IN_STOCK', 'early')]))
        result = m.follow([e], reports, '2026-10-30T12:00:00Z')
        self.assertEqual(result['events'][0]['windows'][0]['status'], 'PENDING_HORIZON')

    def test_failed_capture_not_negative_outcome(self):
        e, reports = fixture();reports.append(dict(observations=[row('2026-10-30T18:00:00Z', sha='failed', status='FAILED')]))
        result = m.follow([e], reports, '2026-10-31T02:00:00Z')
        self.assertEqual(result['events'][0]['windows'][0]['status'], 'MISSING_WINDOW_OBSERVATION')
        self.assertEqual(m.stock_estimates(result)['estimates'][0]['sample_count'], 0)

    def test_target_snapshot_measured(self):
        e, reports = fixture();reports.append(dict(observations=[row('2026-10-30T20:00:00Z', 'IN_STOCK', 'later')]))
        result = m.follow([e], reports, '2026-10-30T21:00:00Z')
        w = result['events'][0]['windows'][0]
        self.assertEqual(w['status'], 'MEASURED')
        self.assertEqual(w['availability'], 'IN_STOCK')
        estimate = m.stock_estimates(result)['estimates'][0]
        self.assertEqual(estimate['sample_count'], 1)
        self.assertEqual(estimate['in_stock_count'], 1)
        self.assertIsNone(estimate['estimated_probability'])

    def test_late_capture_not_backfilled_into_window(self):
        e, reports = fixture();reports.append(dict(observations=[row('2026-10-31T02:00:00Z', 'IN_STOCK', 'late')]))
        result = m.follow([e], reports, '2026-10-31T03:00:00Z')
        self.assertEqual(result['events'][0]['windows'][0]['status'], 'MISSING_WINDOW_OBSERVATION')

    def test_future_rows_not_observed(self):
        e, reports = fixture();reports.append(dict(observations=[row('2026-11-01T02:00:00Z', 'IN_STOCK', 'future')]))
        result = m.follow([e], reports, '2026-10-30T12:00:00Z')
        self.assertEqual(result['events'][0]['latest_availability'], 'OUT_OF_STOCK')

    def test_unknown_stock_not_bernoulli_trial(self):
        e, reports = fixture();reports.append(dict(observations=[row('2026-10-30T20:00:00Z', 'UNKNOWN', 'unknown')]))
        result = m.follow([e], reports, '2026-10-30T21:00:00Z')
        self.assertEqual(m.stock_estimates(result)['estimates'][0]['sample_count'], 0)


if __name__ == '__main__': unittest.main()
