import json
import unittest
from intelligence.tcgdex_catalogue_review import inspect_tcgdex_sets
class TCGdexCatalogueTests(unittest.TestCase):
 def test_catalogue_not_sale_or_sealed_product(self):
  data=json.dumps([{"id":"swsh1","name":"Épée et Bouclier"}]).encode()
  result=inspect_tcgdex_sets(data,observed_at="2026-10-29T01:00:00Z")
  self.assertEqual(result["set_count"],1)
  self.assertFalse(result["sealed_product_catalogue"])
  self.assertFalse(result["market_offer_evidence"])
  self.assertFalse(result["purchase_authorized"])
 def test_duplicate_set_rejected(self):
  data=json.dumps([{"id":"x","name":"A"},{"id":"x","name":"B"}]).encode()
  with self.assertRaises(ValueError):
   inspect_tcgdex_sets(data,observed_at="2026-10-29T01:00:00Z")
 def test_empty_catalogue_rejected(self):
  with self.assertRaises(ValueError):
   inspect_tcgdex_sets(b"[]",observed_at="2026-10-29T01:00:00Z")
 def test_blank_identity_rejected(self):
  with self.assertRaises(ValueError):
   inspect_tcgdex_sets(json.dumps([{"id":" x ","name":"Set"}]).encode(),observed_at="2026-10-29T01:00:00Z")
 def test_non_list_rejected(self):
  with self.assertRaises(ValueError):
   inspect_tcgdex_sets(b'{"id":"x"}',observed_at="2026-10-29T01:00:00Z")
if __name__=="__main__":unittest.main()
