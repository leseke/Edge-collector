import unittest
from intelligence.retail_radar import normalize_offer
from intelligence.retail_transition_engine import detect_retail_transitions
BASE=dict(source_id="store",source_domain="example.org",listing_url="https://example.org/item",actual_seller="Seller",product_key="sku",vertical="LEGO")
def sample(at,state,price):
 return normalize_offer(**BASE,observed_at=at,offer_state=state,price_eur=price)
class TransitionTests(unittest.TestCase):
 def test_restock_not_proven(self):
  a=sample("2026-10-27T10:00:00Z","OUT_OF_STOCK","100")
  b=sample("2026-10-27T11:00:00Z","IN_STOCK","100")
  e=detect_retail_transitions([a,b])
  self.assertEqual(e[0]["event"],"RESTOCK_CANDIDATE")
  self.assertFalse(e[0]["physical_restock_proven"])
 def test_price_change(self):
  a=sample("2026-10-27T10:00:00Z","IN_STOCK","100")
  b=sample("2026-10-27T11:00:00Z","IN_STOCK","90")
  self.assertEqual(detect_retail_transitions([a,b])[0]["event"],"PRICE_CHANGE_CANDIDATE")
 def test_one_observation_no_event(self):
  self.assertEqual(detect_retail_transitions([sample("2026-10-27T10:00:00Z","IN_STOCK","100")]),[])
 def test_same_time_rejected(self):
  a=sample("2026-10-27T10:00:00Z","OUT_OF_STOCK","100")
  b=sample("2026-10-27T10:00:00Z","IN_STOCK","100")
  with self.assertRaises(ValueError):detect_retail_transitions([a,b])
if __name__=="__main__":unittest.main()
