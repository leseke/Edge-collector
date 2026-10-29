import unittest
from intelligence.bricklink_oauth_client import build_signed_request,fetch_sold_aggregate
C={"consumer_key":"key","consumer_secret":"secret","token":"access","token_secret":"token-secret"}
P={"meta":{"code":200},"data":{"item":{"type":"SET","no":"10365-1"},"new_or_used":"N",
"currency_code":"EUR","min_price":"110","max_price":"150","avg_price":"130","qty_avg_price":"125",
"unit_quantity":3,"total_quantity":5}}
class OAuthClientTests(unittest.TestCase):
 def test_signature_and_no_credentials_in_url(self):
  r=build_signed_request(set_no="10365-1",condition="N",currency="EUR",**C,timestamp=1780000000,nonce="abcdefghij")
  self.assertIn("guide_type=sold",r["url"])
  self.assertNotIn("secret",r["url"])
  self.assertIn("oauth_signature=",r["headers"]["Authorization"])
 def test_read_only_aggregate(self):
  x=fetch_sold_aggregate(set_no="10365-1",observed_at="2026-10-27T10:00:00Z",credentials=C,transport=lambda _:P)
  self.assertEqual(x["units"],5)
  self.assertFalse(x["outcome_learning_eligible"])
 def test_non_success_api_rejected(self):
  with self.assertRaises(ValueError):fetch_sold_aggregate(set_no="10365-1",observed_at="2026-10-27T10:00:00Z",credentials=C,transport=lambda _:{**P,"meta":{"code":429}})
 def test_invalid_set_rejected(self):
  with self.assertRaises(ValueError):build_signed_request(set_no="../orders",condition="N",currency="EUR",**C)
 def test_credentials_required(self):
  with self.assertRaises(ValueError):fetch_sold_aggregate(set_no="10365-1",observed_at="2026-10-27T10:00:00Z",credentials={})
if __name__=="__main__":unittest.main()
