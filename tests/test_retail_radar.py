import unittest
from intelligence.retail_radar import normalize_offer
from intelligence.tcg_retail_sources import classify_retail_offer
P=dict(source_id="store",source_domain="example.org",listing_url="https://shop.example.org/item",
 actual_seller="Store",product_key="sku-001",vertical="LEGO",offer_state="IN_STOCK",
 observed_at="2026-10-27T14:00:00Z",price_eur="125.00")
class GeneralRetailRadarTests(unittest.TestCase):
 def test_cross_market_schema(self):
  for vertical in ("TCG","LEGO","SNEAKERS","WATCHES","LIMITED_APPAREL","COLLECTIBLES"):
   result=normalize_offer(**{**P,"vertical":vertical})
   self.assertEqual(result["vertical"],vertical)
   self.assertFalse(result["scarcity_inferred"])
   self.assertFalse(result["completed_sale_evidence"])
 def test_observed_stock_does_not_prove_restock(self):
  row=normalize_offer(**{**P,"event":"RESTOCK_CANDIDATE"})
  self.assertFalse(row["event_confirmed"])
 def test_marketplace_domain_spoof_rejected(self):
  with self.assertRaises(ValueError):normalize_offer(**{**P,"listing_url":"https://shop.example.org.bad.net/p"})
 def test_nan_rejected(self):
  with self.assertRaises(ValueError):normalize_offer(**{**P,"price_eur":"NaN"})
 def test_old_tcg_registry_remains_compatible(self):
  row=classify_retail_offer(source_id="fnac",listing_url="https://www.fnac.com/product",
   actual_seller="Seller",product_key="sku",offer_state="PREORDER",observed_at=P["observed_at"])
  self.assertEqual(row["common_radar"]["vertical"],"TCG")
  self.assertFalse(row["common_radar"]["purchase_authorized"])
if __name__=="__main__":unittest.main()
