import tempfile
import unittest
from pathlib import Path
from intelligence.bricklink_observation_journal import append_observation
from intelligence.bricklink_sold_aggregate import parse_bricklink_sold_priceguide
DATA={"data":{"item":{"type":"SET","no":"10365-1"},"new_or_used":"N","currency_code":"EUR","min_price":"100","max_price":"180","avg_price":"140","qty_avg_price":"130","unit_quantity":2,"total_quantity":4}}
def obs():
 return parse_bricklink_sold_priceguide(DATA,set_no="10365-1",condition="N",currency="EUR",observed_at="2026-10-27T10:00:00Z")
class ObservationJournalTests(unittest.TestCase):
 def test_append_and_deduplicate(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"research.jsonl"
   a=append_observation(p,obs())
   self.assertEqual(append_observation(p,obs())["id"],a["id"])
   self.assertEqual(len(p.read_text().splitlines()),1)
 def test_conflicting_observation_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"research.jsonl";append_observation(p,obs())
   altered={**obs(),"units":99}
   with self.assertRaises(ValueError):append_observation(p,altered)
 def test_untrusted_promotion_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   altered={**obs(),"outcome_learning_eligible":True}
   with self.assertRaises(ValueError):append_observation(Path(d)/"research.jsonl",altered)
if __name__=="__main__":unittest.main()
