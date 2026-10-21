import json
import os
import tempfile
import unittest
from intelligence.transaction_ingest import import_candidates, prepare_candidate

BASE = dict(product_id='pokemon-sc-001', marketplace='example', sold_at='2026-10-20T10:00:00+00:00',
            observed_at='2026-10-21T10:00:00+00:00', price='40.50', currency='EUR',
            territory='FR', evidence_url='https://example.org/sale/1',
            evidence_kind='platform_sold_record', source_method='manual_review')


class TransactionTests(unittest.TestCase):
    def test_candidate_never_verified(self):
        x = prepare_candidate(BASE)
        self.assertEqual(x['status'], 'unverified')
        self.assertNotIn('decision', x)

    def test_refuse_listings(self):
        with self.assertRaises(ValueError):
            prepare_candidate({**BASE, 'evidence_kind': 'listing'})

    def test_refuse_decision(self):
        with self.assertRaises(ValueError):
            prepare_candidate({**BASE, 'financial_decision': 'BUY'})

    def test_refuse_fake_amount_and_time(self):
        for update in ({'price': -1}, {'price': 'nan'}, {'price': '4.123'},
                       {'sold_at': '2027-01-01T00:00:00+00:00'}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                prepare_candidate({**BASE, **update})

    def test_append_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'sales.jsonl')
            self.assertEqual(import_candidates(path, [BASE, BASE]), 1)
            self.assertEqual(import_candidates(path, [BASE]), 0)
            with open(path, encoding='utf-8') as f:
                entries = [json.loads(line) for line in f]
            self.assertEqual(len(entries), 1)

    def test_validate_all_before_writing(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'sales.jsonl')
            with self.assertRaises(ValueError):
                import_candidates(path, [BASE, {**BASE, 'evidence_kind': 'listing'}])
            self.assertFalse(os.path.exists(path))

if __name__ == '__main__':
    unittest.main()
