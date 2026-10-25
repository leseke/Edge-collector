import unittest
from intelligence.mri_evidence_segments import segment_page
from intelligence.mri_evidence_events import extract_candidates

class EventCandidateTests(unittest.TestCase):
 def test_late_page_event_is_detected_with_evidence(self):
  text="Neutral descriptions. "*180+" Réimpression announced near the end."
  evidence=segment_page("pk","https://www.pokemon.com",f"<p>{text}</p>",max_chars=500)
  result=extract_candidates(evidence,"2026-10-25T08:00:00Z")
  self.assertEqual(result["coverage"],"COMPLETE")
  self.assertEqual(result["scanned_characters"],len(text.strip()))
  self.assertTrue(any(x["action_type"]=="reprint" and "Réimpression" in x["quote"] for x in result["candidates"]))
  self.assertTrue(all(x["verification_status"]=="CANDIDATE_UNVERIFIED" and x["occurred_at"] is None for x in result["candidates"]))
 def test_no_assertion_without_keyword(self):
  evidence=segment_page("a","https://www.lego.com","No evidence or event recorded today.")
  self.assertFalse(extract_candidates(evidence,"2026-10-25T08:00:00Z")["candidates"])
 def test_corrupt_hash_is_rejected(self):
  evidence=segment_page("a","https://www.lego.com","A new launch was described in this article.")
  evidence["source_sha256"]="0"*64
  with self.assertRaises(ValueError):extract_candidates(evidence,"2026-10-25T08:00:00Z")
 def test_no_unqualified_evidence(self):
  evidence=segment_page("a","https://www.lego.com","A new launch was described in this article.")
  evidence["complete"]=False
  with self.assertRaises(ValueError):extract_candidates(evidence,"2026-10-25T08:00:00Z")
if __name__=="__main__":unittest.main()
