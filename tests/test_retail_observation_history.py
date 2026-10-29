import tempfile
import unittest
from pathlib import Path
from intelligence.retail_radar import normalize_offer
from intelligence.retail_observation_history import append_retail_observation,summarize_retail_history
BASE=dict(source_id="store",source_domain="example.org",listing_url="https://example.org/item",
actual_seller="Seller",product_key="lego-10365",vertical="LEGO",price_eur="100")
def item(hour,state,price="100"):
 return normalize_offer(**{**BASE,"offer_state":state,"price_eur":price,
 "observed_at":f"2026-10-28T{hour:02d}:00:00Z"})
class HistoryTests(unittest.TestCase):
 def test_dedup_and_no_ground_truth_fabrication(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"journal.jsonl"
   a=append_retail_observation(p,item(9,"OUT_OF_STOCK"))
   b=append_retail_observation(p,item(9,"OUT_OF_STOCK"))
   self.assertTrue(a["appended"]);self.assertFalse(b["appended"])
   append_retail_observation(p,item(10,"IN_STOCK"))
   append_retail_observation(p,item(11,"IN_STOCK"))
   summary=summarize_retail_history(p,as_of="2026-10-28T12:00:00Z")
   self.assertEqual(summary["observations"],3)
   self.assertEqual(summary["source_reconfirmed"],1)
   self.assertIsNone(summary["false_positive_rate"])
 def test_conflicting_same_time_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"journal.jsonl"
   append_retail_observation(p,item(9,"OUT_OF_STOCK"))
   with self.assertRaises(ValueError):append_retail_observation(p,item(9,"IN_STOCK"))
 def test_as_of_excludes_future_observations(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"journal.jsonl"
   append_retail_observation(p,item(9,"OUT_OF_STOCK"))
   append_retail_observation(p,item(10,"IN_STOCK"))
   self.assertEqual(summarize_retail_history(p,as_of="2026-10-28T09:30:00Z")["candidate_events"],0)
 def test_corrupt_journal_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"journal.jsonl";p.write_text('{"schema":"edge.retail.history.v1","id":"fake","observation":{}}\n')
   with self.assertRaises(ValueError):summarize_retail_history(p,as_of="2026-10-28T12:00:00Z")
if __name__=="__main__":unittest.main()
