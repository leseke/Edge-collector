import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import discovery_history as m


def publication(title='LEGO 42705 revealed', summary='', **updates):
    row = dict(id='pub1', title=title, summary=summary, observed_at='2026-10-30T00:00:00+00:00',
               source_id='brickset', source_role='SPECIALIST_MEDIA', url='https://brickset.com/article/1',
               published_at='2026-10-29T15:00:00+00:00', content_sha256='hash')
    row.update(updates)
    return row


class DiscoveryTests(unittest.TestCase):
    def test_multiple_explicit_references(self):
        self.assertEqual(m.references(publication('New sets (42709 42718 42719)')), ['42709', '42718', '42719'])

    def test_official_summary_reference(self):
        self.assertEqual(m.references(publication('New Icons set', 'The LEGO Group reveals Venetian Neighbourhood (11388) set.')), ['11388'])

    def test_year_price_and_piece_counts(self):
        self.assertEqual(m.references(publication('New LEGO sets in 2027', 'With 5,682 pieces and a $100 price.')), [])

    def test_daily_historical_feature_not_launch(self):
        self.assertEqual(m.references(publication('Random figure of the day', 'One set, 75365 Yavin 4 Rebel Base.')), [])

    def test_statistical_roundup_not_launch(self):
        self.assertEqual(m.references(publication("What's hot this week", '11388 Venetian Neighbourhood 13472 Views')), [])

    def test_ids_and_evidence_persist(self):
        first = m.build_candidates([publication()], [], '2026-10-30T00:00:00+00:00')
        second = m.build_candidates([publication()], [dict(observed_at='2026-10-30T00:00:00+00:00', candidates=first)], '2026-10-30T06:00:00+00:00')
        self.assertEqual(first[0]['id'], second[0]['id'])
        self.assertEqual(second[0]['first_observed_at'], first[0]['first_observed_at'])
        self.assertEqual(len(second[0]['evidence']), 1)
        self.assertFalse(second[0]['buy_signal'])

    def test_candidates_survive_leaving_feed(self):
        first = m.build_candidates([publication()], [], '2026-10-30T00:00:00+00:00')
        second = m.build_candidates([], [dict(observed_at='2026-10-30T00:00:00+00:00', candidates=first)], '2026-10-31T00:00:00+00:00')
        self.assertEqual(len(second), 1)

    def test_corroboration_is_separate_evidence(self):
        rows = m.build_candidates([publication(), publication(id='pub2', source_id='lego', source_role='MANUFACTURER')], [], '2026-10-30T00:00:00+00:00')
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]['evidence']), 2)

    def test_probe_rotation(self):
        rows = m.build_candidates([publication('New LEGO sets (42709 42718 42719 67005)')], [], '2026-10-30T00:00:00+00:00')
        selected = m.select_probes(rows)
        self.assertEqual(len(selected), 3)
        for row in selected:
            row['last_probe_at'] = '2026-10-30T00:00:00+00:00'
        self.assertNotIn(m.select_probes(rows)[0]['id'], [r['id'] for r in selected])

    def test_review_control_uses_most_recent(self):
        rows = m.build_candidates([publication('Review: 30762 Batman', id='old', published_at='2026-10-20T00:00:00+00:00'),
                                   publication('Review: 42705 Cabin'),
                                   publication('LEGO 42718 and 42719 announced', id='new')], [], '2026-10-30T00:00:00+00:00')
        self.assertEqual(m.select_probes(rows)[2]['id'], 'lego_42705')

    def test_network_failure_is_not_empty_market(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder, patch.object(m, 'urlopen', side_effect=TimeoutError('timeout')):
            result = m.probe({'id': 'lego_42705', 'sku': '42705'}, Path(folder))
        self.assertEqual(result['status'], 'FAILED')
        self.assertEqual(result['error_type'], 'TimeoutError')


if __name__ == '__main__':
    unittest.main()
