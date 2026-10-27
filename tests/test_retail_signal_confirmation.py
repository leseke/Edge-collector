import unittest
from intelligence.retail_radar import normalize_offer
from intelligence.retail_signal_confirmation import confirm_retail_signals
K=dict(source_id="store",source_domain="example.org",listing_url="https://example.org/item",actual_seller="Store",product_key="sku",vertical="TCG",price_eur="100")
def at(h,state,price="100",seller="Store"):
 return normalize_offer(**{**K,"actual_seller":seller,"observed_at":f"2026-10-27T{h:02d}:00:00Z","offer_state":state,"price_eur":price})
class ConfirmationTests(unittest.TestCase):
 def test_single_restock_unconfirmed(self):
  r=confirm_retail_signals([at(10,"OUT_OF_STOCK"),at(11,"IN_STOCK")])
  self.assertEqual(r[0]["status"],"UNCONFIRMED")
 def test_repeated_restock_reconfirmed_not_physical_proof(self):
  r=confirm_retail_signals([at(10,"OUT_OF_STOCK"),at(11,"IN_STOCK"),at(12,"IN_STOCK")])
  self.assertEqual(r[0]["status"],"SOURCE_RECONFIRMED")
  self.assertFalse(r[0]["physical_stock_verified"])
 def test_reverted_price_not_confirmed(self):
  r=confirm_retail_signals([at(10,"IN_STOCK"),at(11,"IN_STOCK","90"),at(12,"IN_STOCK","100")])
  self.assertEqual(r[0]["status"],"UNCONFIRMED")
 def test_cross_seller_no_mixed_confirmation(self):
  r=confirm_retail_signals([at(10,"OUT_OF_STOCK"),at(11,"IN_STOCK"),at(12,"IN_STOCK",seller="Other")])
  self.assertEqual(r[0]["status"],"UNCONFIRMED")
 def test_confirmations_minimum_enforced(self):
  with self.assertRaises(ValueError):confirm_retail_signals([],minimum_confirmations=1)
if __name__=="__main__":unittest.main()
