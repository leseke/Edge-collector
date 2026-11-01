import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
from seller_reliability import review_seller,purchase_gate,REQUIRED_CHECKS
from coverage_history import source_context
from assessment_history import assess

AT='2026-11-01T10:00:00Z'
URL='https://example.com/product'

def registry():
    return dict(schema='edge.seller.review_registry.v1',reviews=[dict(seller='Store',site_origin='https://example.com',
        status='VERIFIED',reviewed_at='2026-11-01T09:00:00Z',valid_until='2026-11-10T09:00:00Z',
        checks={c:dict(result='PASS',evidence_url='https://evidence.example/'+c,evidence_sha256='a'*64) for c in REQUIRED_CHECKS})])

def row():
    return dict(id='offer',seller='Store',url=URL,product_id='lego_11388',price='599.99',currency='EUR',
        status='OK',price_kind='ASKING_PRICE',availability='IN_STOCK',observed_at=AT,body_sha256='proof',
        source_qualification='ESTABLISHED_RETAILER',evidence={'seller_reliability_reviewed':True})

class SellerPolicyTests(unittest.TestCase):
    def test_source_flags_and_known_brand_qualification_do_not_grant_trust(self):
        p=source_context({'observations':[row()]},AT)['products'][0]
        self.assertEqual(p['sources'][0]['seller_reliability']['status'],'UNVERIFIED')
        self.assertIsNone(p['lowest_reviewed_seller_in_stock_price_eur'])
        self.assertEqual(p['lowest_observed_in_stock_asking_price_eur'],'599.99')
        self.assertEqual(p['purchase_gate']['status'],'BLOCKED')
        self.assertFalse(p['purchase_gate']['buy_signal'])

    def test_complete_documented_review_is_required(self):
        self.assertTrue(review_seller('Store',URL,registry(),AT)['eligible_for_economic_use'])
        for check in REQUIRED_CHECKS:
            r=registry();del r['reviews'][0]['checks'][check]
            self.assertFalse(review_seller('Store',URL,r,AT)['eligible_for_economic_use'])
        r=registry();r['reviews'][0]['checks']['LEGAL_IDENTITY']['evidence_sha256']='missing'
        self.assertFalse(review_seller('Store',URL,r,AT)['eligible_for_economic_use'])

    def test_expired_future_and_excessively_long_reviews_fail_closed(self):
        r=registry()
        self.assertEqual(review_seller('Store',URL,r,'2026-11-11T10:00:00Z')['status'],'EXPIRED')
        self.assertFalse(review_seller('Store',URL,r,'2026-11-01T08:00:00Z')['eligible_for_economic_use'])
        r['reviews'][0]['valid_until']='2027-01-01T09:00:00Z'
        self.assertFalse(review_seller('Store',URL,r,AT)['eligible_for_economic_use'])

    def test_merchant_scope_duplicate_and_wrong_schema_do_not_grant_trust(self):
        r=registry()
        self.assertFalse(review_seller('Store','https://other.example/product',r,AT)['eligible_for_economic_use'])
        self.assertFalse(review_seller('Other',URL,r,AT)['eligible_for_economic_use'])
        r['reviews'].append(copy.deepcopy(r['reviews'][0]))
        self.assertFalse(review_seller('Store',URL,r,AT)['eligible_for_economic_use'])
        r=registry();r['schema']='other'
        self.assertFalse(review_seller('Store',URL,r,AT)['eligible_for_economic_use'])

    def test_verified_unavailable_or_failed_quote_does_not_unlock_gate(self):
        r=row();r['availability']='COMING_SOON'
        p=source_context({'observations':[r]},AT,registry())['products'][0]
        self.assertEqual(p['purchase_gate']['status'],'BLOCKED')
        r['availability']='IN_STOCK';r['status']='FAILED'
        p=source_context({'observations':[r]},AT,registry())['products'][0]
        self.assertEqual(p['purchase_gate']['status'],'BLOCKED')

    def test_valid_seller_review_alone_never_authorizes_purchase(self):
        p=source_context({'observations':[row()]},AT,registry())['products'][0]
        self.assertEqual(p['purchase_gate']['status'],'SELLER_CHECKS_PASSED_OTHER_REQUIREMENTS_PENDING')
        self.assertEqual(p['lowest_reviewed_seller_in_stock_price_eur'],'599.99')
        self.assertFalse(p['purchase_gate']['buy_signal']);self.assertFalse(p['purchase_gate']['purchase_authorized'])
        self.assertEqual(p['purchase_gate']['financial_decision'],'NOT_ESTABLISHED')

    def test_unknown_seller_blocks_even_with_arbitrarily_low_displayed_price(self):
        r=row();r['price']='0.01'
        p=source_context({'observations':[r]},AT)['products'][0]
        self.assertEqual(p['purchase_gate']['seller_eligible_offer_count'],0)
        self.assertIn('UNVERIFIED_SELLER_OFFERS_EXCLUDED_FROM_ECONOMIC_COMPARISONS',p['purchase_gate']['blockers'])

    def test_standalone_gate_does_not_accept_a_bare_eligibility_flag(self):
        s=dict(usable_current_quote=True,availability='IN_STOCK',source_url=URL,
               seller_reliability={'eligible_for_economic_use':True})
        self.assertEqual(purchase_gate([s],AT)['status'],'BLOCKED')

    def test_assessment_persists_blocker_without_dropping_market_fact(self):
        c=dict(id='lego_11388',sku='11388',evidence=[])
        case=assess(c,{'observations':[row()]},[],{}, {},AT)
        self.assertIn('SELLER_RELIABILITY_UNVERIFIED_OR_EXPIRED',case['missing_data'])
        self.assertEqual(case['seller_purchase_gate']['status'],'BLOCKED')
        self.assertTrue(any(f['type']=='RETAIL_OBSERVATION' for f in case['facts']))
        self.assertFalse(case['buy_signal'])

if __name__=='__main__':unittest.main()
