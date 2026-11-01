import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import forecast_history as m

AT='2026-02-01T12:00:00Z'
MODEL={'id':'model-one','source_sha256':{'fixture':'isolated-test-only'}}

def analogue(probability=.6):
    matches=[] if probability is None else [{'product_id':'prior'+str(i),'measured_outcome':{
        'status':'MEASURED','horizon_hours':24,'observed_at':'2026-01-02T12:00:00Z',
        'availability':'IN_STOCK' if i<3 else 'OUT_OF_STOCK','evidence_sha256':'prior-source-'+str(i)}} for i in range(5)]
    return {'generated_at':AT,'queries':[{'event_id':'event','product_id':'product','configuration':{
        'as_of':'2026-02-01T10:00:00Z','family':'OBSERVED_STOCKOUT','seller':'retailer','currency':'EUR','evidence':[{
            'observed_at':'2026-02-01T10:00:00Z','body_sha256':'source','url':'https://example.com/source'}]},
        'horizons':[{'horizon_hours':24,'analogues':matches,'sample_count':len(matches),
                     'in_stock_count':3 if matches else 0,'minimum_samples':5,'estimated_in_stock_frequency':probability}]}]}

def measured():
    return {'events':[{'id':'event','product_id':'product','source_url':'https://example.com/source','seller':'retailer','currency':'EUR','windows':[{
        'horizon_hours':24,'status':'MEASURED','target_at':'2026-02-02T10:00:00Z',
        'observed_at':'2026-02-02T12:00:00Z','availability':'OUT_OF_STOCK','price':'100','evidence_sha256':'actual-source'}]}]}

class ForecastTests(unittest.TestCase):
    def test_replay_does_not_rewrite_first_issuance(self):
        first=m.freeze(analogue(),[],AT,MODEL)
        later=analogue();later['queries'][0]['horizons'][0]['estimated_in_stock_frequency']=.9
        second=m.freeze(later,[first,first],'2026-02-01T13:00:00Z',MODEL)
        self.assertEqual(first['records'],second['records'])
        self.assertEqual(second['created_this_run'],0)
        self.assertEqual(second['reused_this_run'],1)

    def test_late_registration_is_never_prospective(self):
        ledger=m.freeze(analogue(),[],'2026-02-03T12:00:00Z',MODEL)
        result=m.evaluate(ledger,measured(),'2026-02-03T12:00:00Z')
        self.assertEqual(result['evaluations'][0]['validation_status'],'EXCLUDED_LATE_REGISTRATION')
        self.assertEqual(result['metrics'][0]['scored_count'],0)
        self.assertIsNone(result['metrics'][0]['brier_score'])

    def test_valid_numeric_forecast_is_scored_against_actual_source(self):
        ledger=m.freeze(analogue(),[],AT,MODEL)
        result=m.evaluate(ledger,measured(),'2026-02-03T12:00:00Z')
        self.assertEqual(result['evaluations'][0]['validation_status'],'SCORED_PROSPECTIVE')
        self.assertAlmostEqual(result['metrics'][0]['brier_score'],.36)
        self.assertEqual(result['metrics'][0]['baseline_brier_score'],0)

    def test_abstention_not_counted_as_failure_or_prediction(self):
        ledger=m.freeze(analogue(None),[],AT,MODEL)
        result=m.evaluate(ledger,measured(),'2026-02-03T12:00:00Z')
        self.assertEqual(result['evaluations'][0]['validation_status'],'OBSERVED_AFTER_ABSTENTION_NOT_A_PREDICTION')
        self.assertEqual(result['metrics'][0]['scored_count'],0)
        self.assertEqual(result['metrics'][0]['abstentions'],1)

    def test_missing_capture_not_negative_outcome(self):
        ledger=m.freeze(analogue(),[],AT,MODEL);follow=measured()
        follow['events'][0]['windows'][0]={'horizon_hours':24,'status':'MISSING_WINDOW_OBSERVATION'}
        result=m.evaluate(ledger,follow,'2026-02-03T12:00:00Z')
        self.assertEqual(result['metrics'][0]['missing_target_captures'],1)
        self.assertIsNone(result['metrics'][0]['brier_score'])

    def test_unknown_availability_not_binary_failure(self):
        ledger=m.freeze(analogue(),[],AT,MODEL);follow=measured()
        follow['events'][0]['windows'][0]['availability']='UNKNOWN'
        result=m.evaluate(ledger,follow,'2026-02-03T12:00:00Z')
        self.assertEqual(result['evaluations'][0]['validation_status'],'UNKNOWN_TARGET_AVAILABILITY')
        self.assertEqual(result['metrics'][0]['scored_count'],0)

    def test_modified_old_record_or_conflicting_replay_rejected(self):
        ledger=m.freeze(analogue(),[],AT,MODEL)
        altered=copy.deepcopy(ledger);altered['records'][0]['sample_count']=99
        with self.assertRaises(ValueError):m.checked_records([altered],AT)
        row=altered['records'][0]
        row['record_sha256']=m.digest({k:v for k,v in row.items() if k!='record_sha256'})
        with self.assertRaises(ValueError):m.checked_records([ledger,altered],AT)

    def test_estimate_must_match_real_sample(self):
        for probability in (.9,float('nan')):
            with self.assertRaises(ValueError):m.freeze(analogue(probability),[],AT,MODEL)

    def test_future_analogue_outcome_rejected(self):
        data=analogue();data['queries'][0]['horizons'][0]['analogues'][0]['measured_outcome']['observed_at']='2026-02-02T12:00:00Z'
        with self.assertRaises(ValueError):m.freeze(data,[],AT,MODEL)

    def test_future_feature_rejected(self):
        data=analogue();data['queries'][0]['configuration']['evidence'][0]['observed_at']='2026-02-02T12:00:00Z'
        with self.assertRaises(ValueError):m.freeze(data,[],AT,MODEL)

    def test_changed_seller_scope_rejected(self):
        ledger=m.freeze(analogue(),[],AT,MODEL);follow=measured()
        follow['events'][0]['seller']='other seller'
        with self.assertRaises(ValueError):m.evaluate(ledger,follow,'2026-02-03T12:00:00Z')

    def test_outcome_outside_window_rejected(self):
        ledger=m.freeze(analogue(),[],AT,MODEL);follow=measured()
        follow['events'][0]['windows'][0]['observed_at']='2026-02-03T12:00:00Z'
        with self.assertRaises(ValueError):m.evaluate(ledger,follow,'2026-02-03T12:00:00Z')

    def test_new_model_keeps_original_forecasts_and_separate_metrics(self):
        first=m.freeze(analogue(),[],AT,MODEL)
        second=m.freeze(analogue(),[first],AT,dict(MODEL,id='model-two'))
        self.assertEqual(len(second['records']),2)
        report=m.evaluate(second,measured(),'2026-02-03T12:00:00Z')
        self.assertEqual(len(report['metrics']),6)

if __name__=='__main__':unittest.main()
