import json
import unittest
from intelligence.tcgdex_catalogue_intake import collect_tcgdex_fr,URL
class IntakeTests(unittest.TestCase):
 def test_valid_transport_response(self):
  calls=[]
  def transport(url):
   calls.append(url)
   return 200,"application/json",json.dumps([{"id":"swsh1","name":"Epee et Bouclier"}]).encode()
  result=collect_tcgdex_fr(observed_at="2026-10-29T19:00:00Z",transport=transport)
  self.assertEqual(calls,[URL])
  self.assertEqual(result["set_count"],1)
  self.assertFalse(result["market_offer_evidence"])
 def test_http_failure_rejected(self):
  with self.assertRaises(ValueError):
   collect_tcgdex_fr(observed_at="2026-10-29T19:00:00Z",transport=lambda u:(503,"application/json",b"[]"))
 def test_non_json_rejected(self):
  with self.assertRaises(ValueError):
   collect_tcgdex_fr(observed_at="2026-10-29T19:00:00Z",transport=lambda u:(200,"text/html",b"<p>bad</p>"))
if __name__=="__main__":unittest.main()
