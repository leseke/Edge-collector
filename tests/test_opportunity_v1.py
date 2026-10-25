import unittest
from intelligence.opportunity_identity import product_identity,compare_identity
from intelligence.opportunity_economics import evaluate_scenario

P={"category":"TCG","brand":"Pokémon","reference":"SV-001","edition":"Normal","language":"FR","region":"France","condition":"NEW","sealed":True}
class OpportunityV1Tests(unittest.TestCase):
 def test_exact_match(self):
  self.assertTrue(compare_identity(P,dict(P))["financial_comparison_eligible"])
 def test_language_variation(self):
  self.assertEqual(compare_identity(P,{**P,"language":"EN"})["verdict"],"DIFFERENT")
 def test_edition_variation(self):
  self.assertEqual(compare_identity(P,{**P,"edition":"Reverse"})["verdict"],"DIFFERENT")
 def test_unknown_not_confirmed(self):
  self.assertEqual(compare_identity(P,{**P,"language":"unknown"})["verdict"],"DIFFERENT")
  q={**P,"language":"unknown"}
  self.assertEqual(compare_identity(q,q)["verdict"],"UNRESOLVED")
 def test_sealed_and_condition(self):
  self.assertEqual(compare_identity(P,{**P,"sealed":False})["verdict"],"DIFFERENT")
 def test_missing_data_fails(self):
  with self.assertRaises(ValueError):product_identity({k:v for k,v in P.items() if k!="edition"})
 def test_cost_model(self):
  s=evaluate_scenario(buy_price=100,shipping_in=5,sell_price=150,platform_fee=12,shipping_out=6,taxes=0,other_costs=2)
  self.assertEqual(s["net_profit_eur"],"25.00")
  self.assertEqual(s["decision"],"NOT_EVALUATED")
  self.assertFalse(s["execution_authorized"])
 def test_zero_investment_no_roi(self):
  s=evaluate_scenario(buy_price=0,shipping_in=0,sell_price=0,platform_fee=0,shipping_out=0,taxes=0,other_costs=0)
  self.assertIsNone(s["net_roi_pct"])
 def test_nonfinite_money(self):
  with self.assertRaises(ValueError):
   evaluate_scenario(buy_price=float("nan"),shipping_in=0,sell_price=0,platform_fee=0,shipping_out=0,taxes=0,other_costs=0)
 def test_liquidity_not_inferred(self):
  s=evaluate_scenario(buy_price=10,shipping_in=0,sell_price=20,platform_fee=0,shipping_out=0,taxes=0,other_costs=0,sold_evidence_count=5)
  self.assertEqual(s["liquidity_status"],"UNVALIDATED")
if __name__=="__main__":unittest.main()
