import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import probability_history as m


def sample(day, change='5', status='MEASURED'):
    return {'measurements': [{'publication_id': 'publication_' + str(day), 'observation_id': 'retail',
        'anchor': f'2026-10-{day:02d}T12:00:00Z', 'windows': [{'status': status, 'horizon_hours': 24,
        'asking_price_change_pct': change, 'before_evidence_sha256': 'before_' + str(day),
        'after_evidence_sha256': 'after_' + str(day), 'after_observed_at': f'2026-10-{day+1:02d}T12:00:00Z'}]}]}


class ProbabilityTests(unittest.TestCase):
    def test_no_data_no_fabricated_percentage(self):
        rows = m.estimate([], {})['estimates']
        self.assertTrue(all(r['estimated_probability'] is None for r in rows))

    def test_repeated_snapshots_not_independent_trials(self):
        row = m.estimate([sample(1)] * 20, {'retail': 'lego_42705'})['estimates'][0]
        self.assertEqual(row['sample_count'], 1)
        self.assertIsNone(row['estimated_probability'])

    def test_measured_frequency_and_interval(self):
        row = m.estimate([sample(day, '5' if day <= 3 else '-2') for day in range(1, 6)], {'retail': 'lego_42705'})['estimates'][0]
        self.assertEqual(row['estimated_probability'], .6)
        self.assertLess(row['binomial_reference_interval_95'][0], .6)
        self.assertGreater(row['binomial_reference_interval_95'][1], .6)
        self.assertFalse(row['calibrated_for_future_prediction'])

    def test_missing_windows_not_observations(self):
        row = m.estimate([sample(1, status='AWAITING_OBSERVATION')], {'retail': 'lego_42705'})['estimates'][0]
        self.assertEqual(row['sample_count'], 0)

    def test_no_source_mapping_no_trial(self):
        self.assertEqual(m.estimate([sample(1)], {})['estimates'][0]['sample_count'], 0)

    def test_nonfinite_value_rejected(self):
        self.assertEqual(m.estimate([sample(1, 'NaN')], {'retail': 'lego_42705'})['estimates'][0]['sample_count'], 0)


if __name__ == '__main__': unittest.main()
