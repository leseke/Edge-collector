import unittest
from intelligence.tcg_retail_sources import SOURCES,classify_retail_offer
K=dict(source_id="fnac",listing_url="https://www.fnac.com/a123",actual_seller="Partner TCG",
product_key="pokemon-30ans-fr-sealed",offer_state="IN_STOCK",observed_at="2026-10-27T12:00:00Z")
class TCGRetailSourceTests(unittest.TestCase):
 def test_marketplace_seller_retained(self):
  r=classify_retail_offer(**K)
  self.assertEqual(r["actual_seller"],"Partner TCG")
  self.assertFalse(r["completed_sale_evidence"])
  self.assertFalse(r["seller_verified"])
 def test_unknown_seller_rejected(self):
  with self.assertRaises(ValueError):classify_retail_offer(**{**K,"actual_seller":""})
 def test_phishing_domain_rejected(self):
  with self.assertRaises(ValueError):classify_retail_offer(**{**K,"listing_url":"https://www.fnac.com.bad.example/a"})
 def test_specialist_one_piece_not_pokemon(self):
  self.assertEqual(SOURCES["1piecetcg"]["verticals"],["ONE_PIECE"])
 def test_preorder_is_not_stock(self):
  r=classify_retail_offer(**{**K,"offer_state":"PREORDER"})
  self.assertEqual(r["offer_state"],"PREORDER")
  self.assertFalse(r["stock_independently_verified"])
if __name__=="__main__":unittest.main()
