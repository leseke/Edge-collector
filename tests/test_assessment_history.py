import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import assessment_history as m


def candidate(role='SPECIALIST_MEDIA', context='ANNOUNCEMENT'):
    return dict(id='lego_42705', sku='42705', evidence=[dict(publication_id='p1', source_id='source1',
        source_role=role, signal_context=context, source_url='https://example.com/article',
        published_at='2026-10-29T12:00:00+00:00', title='LEGO 42705 announced', content_sha256='abc')])


def quote(**updates):
    row = dict(id='ldlc_discovered_42705', product_id='lego_42705', status='OK',
        price_kind='ASKING_PRICE', price='92.95', currency='EUR', availability='IN_STOCK',
        seller='LDLC', url='https://www.ldlc.com/fiche/example.html',
        observed_at='2026-10-30T10:00:00+00:00', body_sha256='hash', shipping_eur=None)
    row.update(updates)
    return row


class AssessmentTests(unittest.TestCase):
    def assess(self, c=None, rows=None, history=None, publications=None, stamp='2026-10-30T12:00:00+00:00'):
        return m.assess(c or candidate(), {'observations': rows or []}, history or [],
                        {'measurements': []}, publications or {}, stamp)

    def test_early_hypothesis_without_sales(self):
        case = self.assess(candidate(role='MANUFACTURER'))
        self.assertEqual(case['research_priority'], 'HIGH')
        self.assertEqual(case['early_hypothesis']['status'], 'UNTESTED_HYPOTHESIS')
        self.assertEqual(case['financial_decision'], 'UNASSESSED')
        self.assertFalse(case['buy_signal'])

    def test_no_offer_does_not_prove_scarcity(self):
        case = self.assess()
        self.assertIn('NO_RECENT_RETAIL_QUOTE', case['missing_data'])
        self.assertIn('SUPPLY_AND_REPRINTS_UNKNOWN', case['missing_data'])
        self.assertEqual(case['investment_edge'], 'UNPROVEN')

    def test_failed_quote_not_fact(self):
        case = self.assess(rows=[quote(status='FAILED')])
        self.assertFalse(any(f['type'] == 'RETAIL_OBSERVATION' for f in case['facts']))

    def test_indicative_price_not_executable_offer(self):
        case = self.assess(rows=[quote(price_kind='AGGREGATED_INDICATIVE_LOW')])
        self.assertIn('NO_RECENT_RETAIL_QUOTE', case['missing_data'])

    def test_stale_quote_labelled(self):
        case = self.assess(rows=[quote(observed_at='2026-10-28T10:00:00+00:00')])
        fact = next(f for f in case['facts'] if f['type'] == 'RETAIL_OBSERVATION')
        self.assertFalse(fact['fresh_within_24h'])
        self.assertIn('NO_RECENT_RETAIL_QUOTE', case['missing_data'])

    def test_review_with_quote_is_monitoring(self):
        case = self.assess(candidate(context='REVIEW'), [quote()])
        self.assertEqual(case['research_action'], 'MONITOR_OBSERVATIONS')
        self.assertIn('DELIVERED_PRICE_UNKNOWN', case['missing_data'])

    def test_media_counts_not_independent_demand(self):
        case = self.assess()
        self.assertFalse(case['weak_signals'][0]['demand_measurement'])
        self.assertFalse(case['weak_signals'][0]['independence_verified'])
        self.assertTrue(all(a['motive_verified'] is False for a in case['actor_hypotheses']))

    def test_promotion_needs_regional_terms(self):
        case = self.assess(publications={'p1': {'summary': 'This gift-with-purchase has conditions.'}})
        self.assertEqual(case['context'], 'PROMOTION_CONTEXT')
        self.assertIn('PROMOTION_TERMS_AND_REGION_NOT_VERIFIED', case['missing_data'])

    def test_clock_change_alone_not_revision(self):
        a = self.assess(rows=[quote()])
        m.assign_revisions([a], [], '2026-10-30T12:00:00+00:00')
        b = self.assess(rows=[quote(observed_at='2026-10-30T12:00:00+00:00')], stamp='2026-10-30T13:00:00+00:00')
        changes = m.assign_revisions([b], [{'observed_at': '2026-10-30T12:00:00+00:00', 'assessments': [a]}], '2026-10-30T13:00:00+00:00')
        self.assertEqual(changes[0]['type'], 'UNCHANGED')
        self.assertEqual(b['revision'], 1)

    def test_price_change_revises_case(self):
        a = self.assess(rows=[quote()])
        m.assign_revisions([a], [], '2026-10-30T12:00:00+00:00')
        b = self.assess(rows=[quote(price='89.95')])
        changes = m.assign_revisions([b], [{'observed_at': '2026-10-30T12:00:00+00:00', 'assessments': [a]}], '2026-10-30T13:00:00+00:00')
        self.assertEqual(changes[0]['type'], 'ASSESSMENT_CHANGED')
        self.assertEqual(b['revision'], 2)
        self.assertEqual(b['first_assessed_at'], a['first_assessed_at'])

    def test_future_quote_not_current_fact(self):
        case = self.assess(rows=[quote(observed_at='2026-10-31T12:00:00+00:00')])
        self.assertIn('NO_RECENT_RETAIL_QUOTE', case['missing_data'])


if __name__ == '__main__':
    unittest.main()
