import unittest
from intelligence.bricklink_sold_aggregate import parse_bricklink_sold_priceguide
DATA={"data":{"item":{"no":"10365-1","type":"SET"},"new_or_used":"N",
"currency_code":"EUR","min_price":"100.00","max_price":"180.00",
"avg_price":"130.00","qty_avg_price":"125.00",
"unit_quantity":12,"total_quantity":15,"price_detail":[]}}
KW=dict(set_no="10365-1",condition="N",currency="EUR",observed_at="2026-10-27T10:00:00Z")
class BricklinkAggregateTests(unittest.TestCase):
 def test_valid_aggregate_not_proof_of_individual_sale(self):
  result=parse_bricklink_sold_priceguide(DATA,**KW)
  self.assertEqual(result["window"],"ROLLING_LAST_6_MONTHS")
  self.assertEqual(result["units"],15)
  self.assertFalse(result["outcome_learning_eligible"])
 def test_wrong_set_rejected(self):
  with self.assertRaises(ValueError):parse_bricklink_sold_priceguide(DATA,**{**KW,"set_no":"1234-1"})
 def test_currency_mismatch_rejected(self):
  with self.assertRaises(ValueError):parse_bricklink_sold_priceguide(DATA,**{**KW,"currency":"USD"})
 def test_used_new_mismatch_rejected(self):
  with self.assertRaises(ValueError):parse_bricklink_sold_priceguide(DATA,**{**KW,"condition":"U"})
 def test_inconsistent_stats_rejected(self):
  other={"data":{**DATA["data"],"total_quantity":0}}
  with self.assertRaises(ValueError):parse_bricklink_sold_priceguide(other,**KW)
if __name__=="__main__":unittest.main()
