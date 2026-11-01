import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import mri_case_history as m
from coverage_history import source_context
from collection_policy import research_capacity

AT='2026-11-01T10:00:00Z'

def fixture():
    rows=[dict(id='retailer'+str(i),product_id='lego_11383',seller=s,url='https://example.com/'+s,
               price=p,currency='EUR',status='OK',price_kind='ASKING_PRICE',availability='IN_STOCK',
               observed_at='2026-11-01T09:00:00Z',body_sha256=s+'-raw') for i,(s,p) in enumerate([('LDLC','104.95'),('JoueClub','109.99')])]
    market=dict(observations=rows)
    candidate=dict(id='lego_11383',sku='11383',first_observed_at='2026-10-30T16:00:00Z',evidence=[dict(
        publication_id='pub',title='How 11383 Mayor Manor looks with 10228 Haunted House',
        published_at='2026-10-30T14:00:00Z',source_url='https://example.com/publication',
        signal_context='MENTION',source_role='SPECIALIST_MEDIA',content_sha256='publication-raw')])
    return candidate,market,source_context(market,AT)

class MriCaseTests(unittest.TestCase):
    def test_real_scope_and_publication_relationship_not_causality(self):
        c,market,context=fixture();r=m.build([c],context,[market],{},AT)
        self.assertEqual(r['publication_linked_cases'],1)
        case=r['cases'][0]
        self.assertEqual(len(case['retail_sources']),2)
        self.assertEqual(case['measured_publication_reaction_windows'],0)
        self.assertEqual(case['reaction_status'],'PUBLICATION_REACTION_NOT_MEASURED')
        self.assertFalse(case['causality_proven'])
        self.assertFalse(case['buy_signal'])
        self.assertIsNone(case['retail_sources'][0]['displayed_price_change_since_first_capture_pct'])

    def test_variation_requires_distinct_timestamps(self):
        c,market,context=fixture();previous=copy.deepcopy(market)
        for r in previous['observations']:r.update(price='100',observed_at='2026-10-31T09:00:00Z')
        result=m.build([c],context,[previous,market],{},AT)
        self.assertEqual(result['cases'][0]['retail_sources'][0]['displayed_price_change_since_first_capture_pct'],'4.9500')

    def test_replayed_rows_not_extra_captures(self):
        c,market,context=fixture();r=m.build([c],context,[market,market],{},AT)
        self.assertEqual(r['cases'][0]['retail_sources'][0]['successful_capture_count'],1)

    def test_future_quotes_do_not_change_observed_variation(self):
        c,market,context=fixture();future=copy.deepcopy(market)
        for r in future['observations']:r.update(price='9999',observed_at='2026-11-02T09:00:00Z')
        r=m.build([c],context,[market,future],{},AT)
        self.assertEqual(r['cases'][0]['retail_sources'][0]['latest_observation']['price'],'104.95')

    def test_unrelated_publication_measurement_not_attached(self):
        c,market,context=fixture();measurements={'measurements':[dict(publication_id='other',observation_id='retailer0',windows=[dict(status='MEASURED')])]}
        r=m.build([c],context,[market],measurements,AT)
        self.assertEqual(r['cases'][0]['measured_publication_reaction_windows'],0)

    def test_reused_observation_id_from_other_seller_cannot_enter_case(self):
        c,market,context=fixture()
        row=dict(publication_id='pub',observation_id='retailer0',source_url='https://other.example',
                 seller='Other',product_id='lego_11383',currency='EUR',windows=[dict(status='MEASURED')])
        r=m.build([c],context,[market],{'measurements':[row]},AT)
        self.assertEqual(r['cases'][0]['measured_publication_reaction_windows'],0)
        row.update(source_url=market['observations'][0]['url'],seller='LDLC')
        r=m.build([c],context,[market],{'measurements':[row]},AT)
        self.assertEqual(r['cases'][0]['measured_publication_reaction_windows'],1)

    def test_single_current_seller_not_a_multi_source_case(self):
        c,market,context=fixture();market['observations'][1]['status']='FAILED'
        r=m.build([c],source_context(market,AT),[market],{},AT)
        self.assertEqual(r['cases'],[])

    def test_product_without_discovery_publication_stays_a_control(self):
        c,market,context=fixture();r=m.build([],context,[market],{},AT)
        self.assertEqual(r['cases'][0]['case_kind'],'RETAIL_CONTROL_WITHOUT_DISCOVERY_PUBLICATION')
        self.assertEqual(r['publication_linked_cases'],0)

    def test_mention_outside_title_is_not_promoted_to_title_subject(self):
        c,market,context=fixture();c['evidence'][0]['title']='Another reviewed set'
        r=m.build([c],context,[market],{},AT)
        self.assertFalse(r['cases'][0]['publication_evidence'][0]['reference_in_title'])

    def test_verified_upcoming_release_can_have_one_direct_retailer(self):
        c,market,context=fixture();market['observations']=market['observations'][:1]
        primary={'sources':[dict(id='maker',status='VERIFIED_MATCH',source_url='https://example.com/release')],
                 'reviews':[dict(candidate_id=c['id'],current_recheck_verified=True,supported_claims=[dict(
                     kind='ANNOUNCED_GENERAL_RELEASE',source_id='maker',date='2026-11-04')])]}
        r=m.build([c],source_context(market,AT),[market],{},AT,primary)
        case=r['cases'][0]
        self.assertEqual(case['announced_release']['date'],'2026-11-04')
        self.assertEqual(case['announced_release']['date_precision'],'DAY')
        self.assertEqual(len(case['retail_sources']),1)
        self.assertFalse(case['buy_signal']);self.assertFalse(case['causality_proven'])
        primary['sources'][0]['status']='FAILED'
        self.assertEqual(m.build([c],source_context(market,AT),[market],{},AT,primary)['cases'],[])
        primary['sources'][0]['status']='VERIFIED_MATCH'
        primary['reviews'][0]['supported_claims'][0]['date']='2026-99-99'
        self.assertEqual(m.build([c],source_context(market,AT),[market],{},AT,primary)['cases'],[])

    def test_capacity_preserves_total_source_limit(self):
        self.assertEqual(research_capacity(8),8)
        self.assertEqual(research_capacity(10),6)
        self.assertEqual(research_capacity(16),0)
        with self.assertRaises(ValueError):research_capacity(17)

if __name__=='__main__':unittest.main()
