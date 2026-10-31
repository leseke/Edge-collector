import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import assessment_history as m


def candidate():
    return dict(id='lego_42705', sku='42705', evidence=[dict(publication_id='p1', source_id='source1',
        source_role='SPECIALIST_MEDIA', signal_context='ANNOUNCEMENT', source_url='https://example.com/article',
        published_at='2026-10-29T12:00:00+00:00', title='LEGO 42705 announced', content_sha256='abc')])


def quote(**updates):
    row = dict(id='ldlc_discovered_42705', product_id='lego_42705', status='OK',
        price_kind='ASKING_PRICE', price='92.95', currency='EUR', availability='IN_STOCK',
        seller='LDLC', url='https://www.ldlc.com/fiche/example.html',
        observed_at='2026-10-30T10:00:00+00:00', body_sha256='hash', shipping_eur=None)
    row.update(updates)
    return row


class AssessmentTests(unittest.TestCase):
    def assess(self, rows=None, stamp='2026-10-30T12:00:00+00:00'):
        return m.assess(candidate(), {'observations': rows or []}, [], {'measurements': []}, {}, stamp)

    def test_no_generated_narratives_or_priorities(self):
        case = self.assess()
        for key in ('early_hypothesis', 'actor_hypotheses', 'scenarios', 'research_priority', 'weak_signals'):
            self.assertNotIn(key, case)

    def test_publication_is_a_sourced_fact(self):
        fact = self.assess()['facts'][0]
        self.assertEqual(fact['type'], 'PUBLICATION_REFERENCE')
        self.assertEqual(fact['source_url'], 'https://example.com/article')

    def test_failed_quote_not_real_price(self):
        self.assertFalse(any(f['type'] == 'RETAIL_OBSERVATION' for f in self.assess([quote(status='FAILED')])['facts']))

    def test_indicative_price_not_retail_quote(self):
        self.assertIn('NO_RECENT_RETAIL_QUOTE', self.assess([quote(price_kind='AGGREGATED_INDICATIVE_LOW')])['missing_data'])

    def test_old_quote_keeps_date_and_staleness(self):
        case = self.assess([quote(observed_at='2026-10-28T10:00:00+00:00')])
        fact = next(f for f in case['facts'] if f['type'] == 'RETAIL_OBSERVATION')
        self.assertFalse(fact['fresh_within_24h'])
        self.assertEqual(fact['observed_at'], '2026-10-28T10:00:00+00:00')

    def test_unknown_shipping_and_sale_remain_unknown(self):
        case = self.assess([quote()])
        fact = next(f for f in case['facts'] if f['type'] == 'RETAIL_OBSERVATION')
        self.assertIsNone(fact['shipping_eur'])
        self.assertFalse(fact['completed_sale'])
        self.assertIn('NET_MARGIN_NOT_MEASURED', case['missing_data'])

    def test_identical_capture_does_not_change_revision(self):
        a = self.assess([quote()]);m.assign_revisions([a], [], '2026-10-30T12:00:00Z')
        b = self.assess([quote(observed_at='2026-10-30T12:00:00+00:00')], '2026-10-30T13:00:00Z')
        changes = m.assign_revisions([b], [{'observed_at': '2026-10-30T12:00:00Z', 'assessments': [a]}], '2026-10-30T13:00:00Z')
        self.assertEqual(changes[0]['type'], 'UNCHANGED')

    def test_price_change_is_observed_revision(self):
        a = self.assess([quote()]);m.assign_revisions([a], [], '2026-10-30T12:00:00Z')
        b = self.assess([quote(price='89.95')])
        changes = m.assign_revisions([b], [{'observed_at': '2026-10-30T12:00:00Z', 'assessments': [a]}], '2026-10-30T13:00:00Z')
        self.assertEqual(changes[0]['type'], 'OBSERVATIONS_CHANGED')
        self.assertEqual(b['revision'], 2)

    def test_future_quote_not_observed_current_price(self):
        self.assertIn('NO_RECENT_RETAIL_QUOTE', self.assess([quote(observed_at='2026-10-31T12:00:00Z')])['missing_data'])


if __name__ == '__main__': unittest.main()
