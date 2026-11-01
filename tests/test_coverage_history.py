import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import coverage_history as m

AT='2026-11-01T08:00:00Z'

def row(stamp,**updates):
    r=dict(id='retailer',product_id='lego_75639',seller='LDLC',url='https://example.com/offer',
           currency='EUR',price='129.95',price_kind='ASKING_PRICE',status='OK',
           observed_at=stamp,availability='IN_STOCK',body_sha256='actual-source')
    r.update(updates);return r

def followup():
    return {'events':[dict(id='event',product_id='lego_75639',observation_id='retailer',
        source_url='https://example.com/offer',seller='LDLC',currency='EUR',windows=[dict(
        horizon_hours=24,status='MISSING_WINDOW_OBSERVATION',target_at='2026-10-31T22:00:00Z')]) ]}

def report(stamp,rows):return dict(observed_at=stamp,observations=rows)

class CoverageTests(unittest.TestCase):
    def test_absent_archival_run_and_late_capture_not_backfilled(self):
        before=row('2026-10-31T21:00:00Z');after=row('2026-11-01T06:00:00Z')
        r=m.audit(followup(),[report(before['observed_at'],[before]),report(after['observed_at'],[after])],AT)
        incident=r['missed_targets'][0]
        self.assertEqual(incident['diagnosis'],'NO_ARCHIVED_CAPTURE_RUN_IN_TARGET_WINDOW')
        self.assertEqual(incident['successful_capture_gap_hours'],9)
        self.assertFalse(incident['missing_outcome_filled'])
        self.assertFalse(incident['scheduler_root_cause_proven'])

    def test_source_failure_distinguished_from_missing_run(self):
        failed=row('2026-11-01T01:00:00Z',status='FAILED',error='timeout')
        incident=m.audit(followup(),[report(failed['observed_at'],[failed])],AT)['missed_targets'][0]
        self.assertEqual(incident['diagnosis'],'SOURCE_REQUESTS_FAILED_IN_TARGET_WINDOW')
        self.assertEqual(incident['archived_runs_in_window'],1)

    def test_source_not_monitored_in_existing_run(self):
        r=report('2026-11-01T01:00:00Z',[row('2026-11-01T01:00:00Z',id='other')])
        incident=m.audit(followup(),[r],AT)['missed_targets'][0]
        self.assertEqual(incident['diagnosis'],'SOURCE_NOT_OBSERVED_IN_ARCHIVED_TARGET_RUNS')

    def test_contradictory_followup_detected(self):
        r=report('2026-11-01T01:00:00Z',[row('2026-11-01T01:00:00Z')])
        self.assertEqual(m.audit(followup(),[r],AT)['missed_targets'][0]['diagnosis'],'FOLLOWUP_AND_SOURCE_EVIDENCE_DISAGREE')

    def test_future_captures_not_used(self):
        r=report('2026-11-02T01:00:00Z',[row('2026-11-02T01:00:00Z')])
        incident=m.audit(followup(),[r],AT)['missed_targets'][0]
        self.assertIsNone(incident['first_success_after'])

    def test_mixed_stock_is_not_global_shortage_and_cheapest_stockout_not_buyable_floor(self):
        data=report(AT,[row(AT),row(AT,id='king',seller='King Jouet France',price='103.99',availability='OUT_OF_STOCK')])
        p=m.source_context(data,AT)['products'][0]
        self.assertEqual(p['availability_context'],'MIXED_AVAILABILITY_ON_OBSERVED_SOURCES')
        self.assertEqual(p['lowest_observed_in_stock_asking_price_eur'],'129.95')
        self.assertEqual(p['verified_current_seller_count'],2)
        self.assertFalse(p['market_wide_shortage_proven'])
        self.assertFalse(p['buy_signal'])

    def test_duplicate_seller_is_not_independent_coverage(self):
        p=m.source_context(report(AT,[row(AT),row(AT,id='second-page')]),AT)['products'][0]
        self.assertEqual(p['verified_current_seller_count'],1)

    def test_failed_stale_or_nonfinite_quotes_not_current_prices(self):
        for r in [row(AT,status='FAILED'),row('2026-10-29T08:00:00Z'),row(AT,price='NaN'),row(AT,currency='USD')]:
            p=m.source_context(report(AT,[r]),AT)['products'][0]
            self.assertEqual(p['verified_current_seller_count'],0)
            self.assertIsNone(p['sources'][0]['displayed_price_eur'])
            self.assertEqual(p['sources'][0]['availability'],'UNKNOWN')

    def test_indicative_card_index_excluded_from_retail_comparison(self):
        self.assertEqual(m.source_context(report(AT,[row(AT,price_kind='AGGREGATED_INDICATIVE_LOW')]),AT)['products'],[])

    def test_all_observed_stockouts_remain_scoped(self):
        p=m.source_context(report(AT,[row(AT,availability='OUT_OF_STOCK'),row(AT,seller='King Jouet France',availability='OUT_OF_STOCK')]),AT)['products'][0]
        self.assertEqual(p['availability_context'],'OUT_OF_STOCK_ON_MULTIPLE_OBSERVED_SOURCES')
        self.assertFalse(p['market_wide_shortage_proven'])



class PreparationTests(unittest.TestCase):
    def build(self,rows,current_rows=None):
        market=report(AT,current_rows if current_rows is not None else [rows[-1]])
        return m.preparation(m.source_context(market,AT),[report(AT,rows)],AT)['products'][0]

    def test_recent_series_keeps_traceable_baseline_and_expiry(self):
        p=self.build([row('2026-11-01T04:00:00Z'),row('2026-11-01T07:00:00Z')]);s=p['sources'][0]
        self.assertEqual(s['status'],'RECENT_SERIES')
        self.assertEqual(s['recent_distinct_capture_count'],2)
        self.assertEqual(s['recent_max_gap_hours'],3)
        self.assertEqual(s['latest_valid_evidence']['body_sha256'],'actual-source')
        self.assertEqual(s['potential_baseline_expires_at'],'2026-11-02T07:00:00+00:00')
        self.assertEqual(p['recent_baseline_seller_count'],1)

    def test_replayed_quote_or_other_page_is_not_an_extra_capture(self):
        r=row('2026-11-01T07:00:00Z')
        p=self.build([r,r,dict(r,id='other-page',url='https://example.com/other')], [r])
        self.assertEqual(p['sources'][0]['recent_distinct_capture_count'],1)
        self.assertEqual(p['sources'][0]['status'],'SINGLE_RECENT_CAPTURE')

    def test_same_seller_is_not_two_independent_baselines(self):
        r=row('2026-11-01T07:00:00Z');other=dict(r,id='other',url='https://example.com/other')
        self.assertEqual(self.build([r,other],[r,other])['recent_baseline_seller_count'],1)

    def test_stale_capture_cannot_prepare_new_event(self):
        p=self.build([row('2026-10-31T07:59:59Z')])
        self.assertEqual(p['sources'][0]['status'],'STALE_HISTORY')
        self.assertFalse(p['sources'][0]['has_recent_potential_baseline'])

    def test_future_or_invalid_quote_cannot_enter_baseline(self):
        r=row('2026-11-02T07:00:00Z')
        self.assertEqual(self.build([r])['sources'][0]['status'],'NO_VALID_CAPTURE')
        for updates in ({'price':'NaN'},{'body_sha256':None},{'currency':'USD'},{'status':'FAILED'}):
            r=row('2026-11-01T07:00:00Z',**updates)
            self.assertEqual(self.build([r])['sources'][0]['status'],'NO_VALID_CAPTURE')

    def test_failure_retains_prior_evidence_but_exposes_interruption(self):
        a=row('2026-11-01T04:00:00Z');b=row('2026-11-01T07:00:00Z',status='FAILED')
        p=self.build([a,b],[b]);s=p['sources'][0]
        self.assertEqual(s['status'],'COLLECTION_INTERRUPTED')
        self.assertEqual(s['latest_valid_evidence']['observed_at'],a['observed_at'])
        self.assertTrue(s['has_recent_potential_baseline'])

    def test_large_gap_is_exposed_without_interpolation(self):
        s=self.build([row('2026-10-31T22:00:00Z'),row('2026-11-01T07:00:00Z')])['sources'][0]
        self.assertEqual(s['status'],'GAPPED_RECENT_SERIES')
        self.assertEqual(s['recent_distinct_capture_count'],2)
        self.assertEqual(s['recent_max_gap_hours'],9)

    def test_conflicting_same_time_prices_excluded(self):
        a=row('2026-11-01T07:00:00Z');b=dict(a,price='100')
        s=self.build([a,b],[a])['sources'][0]
        self.assertEqual(s['conflicting_timestamps_excluded'],1)
        self.assertEqual(s['status'],'NO_VALID_CAPTURE')

    def test_full_day_boundary_is_included_and_no_financial_signal(self):
        market=report(AT,[row('2026-10-31T08:00:00Z')])
        r=m.preparation(m.source_context(market,AT),[market],AT)
        self.assertEqual(r['products_with_recent_baseline'],1)
        self.assertFalse(r['buy_signal'])
        self.assertFalse(r['predictive_advantage_established'])

if __name__=='__main__':unittest.main()
