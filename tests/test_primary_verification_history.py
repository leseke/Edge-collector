import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import primary_verification_history as p
import assessment_history as a

ROOT = Path(__file__).parents[1]


class PrimaryVerificationTests(unittest.TestCase):
    def source(self):
        return dict(extractor='heading_section', heading_reference='40889', patterns=['130 €', 'Un seul set par foyer'])

    def test_scoped_conditions_pass(self):
        raw = '<h3>Cadeau 40889</h3><p>130 € Un seul set par foyer</p><h3>Autre 40898</h3><p>500 €</p>'.encode()
        self.assertEqual(p.check_source(raw, self.source())['status'], 'VERIFIED_MATCH')

    def test_adjacent_gift_terms_not_borrowed(self):
        raw = '<h3>Cadeau 40889</h3><p>Un seul set par foyer</p><h3>Autre 40898</h3><p>130 €</p>'.encode()
        self.assertEqual(p.check_source(raw, self.source())['status'], 'REVIEW_REQUIRED')

    def test_missing_heading_fails(self):
        with self.assertRaises(ValueError):
            p.check_source(b'<h3>40898</h3><p>130 EUR</p>', self.source())

    def test_price_in_recommendation_without_product_heading_rejected(self):
        with self.assertRaises(ValueError):
            p.extract(b'<h1>Another product</h1><p>499.99 EUR</p>', dict(extractor='product_intro', heading_reference='Le quartier vénitien'))

    def review(self, cid, verified=True):
        plan = json.loads((ROOT / 'research/primary_reviews.json').read_text())
        return dict(observed_at='2026-10-30T12:00:00Z', reviewed_at=plan['reviewed_at'],
                    sources=[dict(id=s['id'], source_url=s['url'], scope=s['scope'], body_sha256='hash') for s in plan['sources']],
                    reviews=[dict(r, current_recheck_verified=verified) for r in plan['reviews'] if r['candidate_id'] == cid])

    def case(self, cid):
        return dict(candidate_id=cid, assessed_at='2026-10-30T12:00:00Z', facts=[],
                    missing_data=['PROMOTION_TERMS_AND_REGION_NOT_VERIFIED', 'REALIZED_SALES_NOT_CONNECTED'],
                    early_hypothesis={'status': 'UNTESTED_HYPOTHESIS'}, research_priority='HIGH')

    def test_french_terms_verified_not_resale_price(self):
        case = self.case('lego_40889')
        a.apply_primary_review(case, self.review('lego_40889'))
        self.assertNotIn('PROMOTION_TERMS_AND_REGION_NOT_VERIFIED', case['missing_data'])
        self.assertTrue(case['primary_verification']['full_local_terms_verified'])
        value = next(f['claim'] for f in case['facts'] if f['claim']['kind'] == 'APPROXIMATE_PROMOTIONAL_VALUE')
        self.assertFalse(value['resale_value_verified'])
        self.assertFalse(value['executable_offer_verified'])

    def test_announcement_does_not_verify_local_terms(self):
        case = self.case('lego_40898')
        a.apply_primary_review(case, self.review('lego_40898'))
        self.assertFalse(case['primary_verification']['full_local_terms_verified'])
        self.assertIn('FRANCE_COMPLETE_GIFT_TERMS_UNCONFIRMED', case['missing_data'])

    def test_failed_recheck_does_not_promote_claims(self):
        case = self.case('lego_40889')
        a.apply_primary_review(case, self.review('lego_40889', False))
        self.assertEqual(case['facts'], [])
        self.assertIn('PROMOTION_TERMS_AND_REGION_NOT_VERIFIED', case['missing_data'])
        self.assertIn('PRIMARY_CLAIMS_NOT_RECHECKED', case['missing_data'])

    def test_main_set_and_gift_same_group(self):
        cases = [self.case(cid) for cid in ('lego_11388', 'lego_40898')]
        for case in cases:
            a.apply_primary_review(case, self.review(case['candidate_id']))
        self.assertEqual(cases[0]['linked_opportunity_group'], cases[1]['linked_opportunity_group'])
        self.assertIsNone(cases[0]['bundle_economics']['net_advantage_eur'])
        self.assertFalse(cases[0]['bundle_economics']['nominal_gift_values_used_as_revenue'])

    def test_past_window_not_urgent_upcoming(self):
        case = self.case('lego_40898')
        case['assessed_at'] = '2026-11-10T12:00:00Z'
        a.apply_primary_review(case, self.review('lego_40898'))
        self.assertEqual(case['event_phase'], 'PAST_WINDOW')
        self.assertEqual(case['research_action'], 'CHECK_POST_EVENT_MARKET')

    def test_current_window_and_upcoming_are_distinct(self):
        for cid, phase in [('lego_40889', 'SOURCE_DATE_WINDOW'), ('lego_40898', 'UPCOMING')]:
            case = self.case(cid)
            a.apply_primary_review(case, self.review(cid))
            self.assertEqual(case['event_phase'], phase)

    def test_blocked_local_page_preserves_scoped_manufacturer_claims(self):
        case = self.case('lego_11388')
        report = self.review('lego_11388')
        review = report['reviews'][0]
        review['supported_claims'] = [c for c in review['claims'] if c['source_id'] == 'lego_venice_press']
        review['unsupported_claims'] = [c for c in review['claims'] if c['source_id'] != 'lego_venice_press']
        a.apply_primary_review(case, report)
        self.assertEqual(case['primary_verification']['status'], 'REVIEWED_CLAIMS_PARTIALLY_RECHECKED')
        kinds = [f['claim']['kind'] for f in case['facts']]
        self.assertIn('PUBLISHED_RECOMMENDED_PRICE_EUR', kinds)
        self.assertNotIn('PUBLISHED_CATALOGUE_PRICE', kinds)
        self.assertIn('FRENCH_CATALOGUE_PRICE_NOT_RECHECKED', case['missing_data'])


if __name__ == '__main__':
    unittest.main()
