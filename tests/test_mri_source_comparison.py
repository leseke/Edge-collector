import unittest
from intelligence.mri_evidence_segments import segment_page
from intelligence.mri_evidence_events import extract_candidates
from intelligence.mri_source_comparison import compare_sources

T="2026-10-25T09:00:00Z"
def doc(sid,url,words):
 return extract_candidates(segment_page(sid,url,"<p>"+words+"</p>"),T)

class CrossSourceTests(unittest.TestCase):
 def test_two_hosts_are_not_proof(self):
  a=doc("p","https://www.pokemon.com/x","A new reprint may be launched next month.")
  b=doc("l","https://www.lego.com/x","A reprint is not confirmed in this story.")
  out=compare_sources([a,b],T)
  g=next(x for x in out["groups"] if x["action_type"]=="reprint")
  self.assertEqual(g["distinct_hosts"],2)
  self.assertFalse(g["same_event_confirmed"])
  self.assertFalse(g["independent_sources_confirmed"])
  self.assertTrue(g["negation_cue_present"])
 def test_one_host_not_multiple_independent_sources(self):
  a=doc("one","https://www.lego.com/a","A launch appeared in news today.")
  b=doc("two","https://www.lego.com/b","Launch commentary was repeated yesterday.")
  x=compare_sources([a,b],T)
  self.assertEqual(x["groups"][0]["distinct_hosts"],1)
 def test_future_observations_not_included(self):
  a=doc("one","https://www.lego.com/a","A launch appeared in news today.")
  self.assertEqual(compare_sources([a],"2026-10-24T09:00:00Z")["groups"],[])
 def test_reject_unqualified_input(self):
  a=doc("one","https://www.lego.com/a","A launch appeared in news today.")
  a["coverage"]="PARTIAL"
  with self.assertRaises(ValueError):compare_sources([a],T)
if __name__=="__main__":unittest.main()
