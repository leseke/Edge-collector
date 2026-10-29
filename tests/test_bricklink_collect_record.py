import tempfile
import unittest
from pathlib import Path
from intelligence.bricklink_collect_record import collect_and_record

C={"consumer_key":"testkey","consumer_secret":"testsecret","token":"testtoken","token_secret":"testtokenpass"}
R={"meta":{"code":200},"data":{"item":{"type":"SET","no":"10365-1"},"new_or_used":"N",
"currency_code":"EUR","min_price":"100","max_price":"170","avg_price":"140",
"qty_avg_price":"132","unit_quantity":3,"total_quantity":6}}
K={"set_no":"10365-1","condition":"N","currency":"EUR",
"observed_at":"2026-10-27T14:00:00Z","credentials":C}
class CollectAndRecordTests(unittest.TestCase):
 def test_collection_is_private_and_idempotent(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/"history.jsonl"
   first=collect_and_record(journal_path=path,transport=lambda _:R,**K)
   second=collect_and_record(journal_path=path,transport=lambda _:R,**K)
   self.assertEqual(first["observation_id"],second["observation_id"])
   self.assertEqual(len(path.read_text().splitlines()),1)
   self.assertEqual(first["learning_verified_outcomes"],0)
   self.assertFalse(first["automated_orders"])
 def test_api_failure_creates_no_observation(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/"history.jsonl"
   with self.assertRaises(ValueError):
    collect_and_record(journal_path=path,transport=lambda _:{**R,"meta":{"code":429}},**K)
   self.assertFalse(path.exists())
 def test_conflicting_same_timestamp_fails_closed(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/"history.jsonl"
   collect_and_record(journal_path=path,transport=lambda _:R,**K)
   altered={"meta":{"code":200},"data":{**R["data"],"total_quantity":7}}
   with self.assertRaises(ValueError):
    collect_and_record(journal_path=path,transport=lambda _:altered,**K)
if __name__=="__main__":unittest.main()
