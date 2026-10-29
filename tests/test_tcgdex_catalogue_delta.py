import unittest
from intelligence.tcgdex_catalogue_delta import compare_catalogue_snapshots
def snap(date,items):
 return {"schema":"edge.tcg.catalogue_review.v1","coverage":"SNAPSHOT_ONLY","observed_at":date,"sets":[{"set_id":k,"set_name":v} for k,v in items]}
class DeltaTests(unittest.TestCase):
 def test_add_rename_remove_not_sales(self):
  a=snap("2026-10-27T00:00:00Z",[("a","Alpha"),("b","Beta")])
  b=snap("2026-10-28T00:00:00Z",[("a","Alpha2"),("c","Gamma")])
  r=compare_catalogue_snapshots(a,b)
  self.assertEqual([x["id"] for x in r["added_sets"]],["c"])
  self.assertEqual([x["id"] for x in r["removed_from_snapshot"]],["b"])
  self.assertEqual([x["id"] for x in r["renamed_sets"]],["a"])
  self.assertFalse(r["removal_proves_discontinuation"])
 def test_wrong_order_rejected(self):
  a=snap("2026-10-28T00:00:00Z",[("a","A")])
  with self.assertRaises(ValueError):compare_catalogue_snapshots(a,a)
 def test_empty_rejected(self):
  a=snap("2026-10-27T00:00:00Z",[("a","A")])
  with self.assertRaises(ValueError):compare_catalogue_snapshots(a,snap("2026-10-28T00:00:00Z",[]))
if __name__=="__main__":unittest.main()
