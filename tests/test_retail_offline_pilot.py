import unittest
from intelligence.retail_offline_pilot import run_offline_retail_pilot
class RetailPilotTests(unittest.TestCase):
 def test_full_pilot_exposes_one_reconfirmation(self):
  r=run_offline_retail_pilot()
  self.assertEqual(r["observations"],6)
  self.assertEqual(r["source_reconfirmed"],1)
  self.assertTrue(r["synthetic_fixture_only"])
  self.assertFalse(r["economic_edge_proven"])
  self.assertIsNone(r["false_positive_rate"])
 def test_cutoff_disallows_future_reconfirmation(self):
  r=run_offline_retail_pilot(as_of="2026-10-28T10:30:00Z")
  self.assertEqual(r["observations"],4)
  self.assertEqual(r["source_reconfirmed"],0)
 def test_no_observations_before_start(self):
  r=run_offline_retail_pilot(as_of="2026-10-28T08:00:00Z")
  self.assertEqual(r["signal_candidates"],0)
if __name__=="__main__":unittest.main()
