import unittest
from intelligence.mri_observation_ingest import normalize_observations,create_research_digest
BASE={"id":"obs1","subject":"LEGO 10365","actor":"LEGO","action":"announcement",
"occurred_at":"2025-08-26T11:00:00+02:00","observed_at":"2025-08-26T12:00:00+02:00",
"source_url":"https://www.lego.com/en-us/aboutus/news/2025/august/lego-icons-captain-jack-sparrow-s-pirate-ship","summary":"New pirate ship announced"}
class IngestTests(unittest.TestCase):
 def test_public_digest_is_not_financial(self):
  d=create_research_digest([BASE]);self.assertEqual(d["status"],"RESEARCH_ONLY");self.assertTrue(d["review_required"]);self.assertEqual(d["decision"],"NOT_EVALUATED")
 def test_observation_not_before_event(self):
  with self.assertRaises(ValueError): normalize_observations([{**BASE,"observed_at":"2025-08-25T00:00:00Z"}])
 def test_no_secrets_or_extra_fields(self):
  with self.assertRaises(ValueError): normalize_observations([{**BASE,"token":"PRIVATE"}])
 def test_unique(self):
  with self.assertRaises(ValueError): normalize_observations([BASE,BASE])
 def test_https_only(self):
  with self.assertRaises(ValueError): normalize_observations([{**BASE,"source_url":"http://example.org"}])
 def test_requires_timezone(self):
  with self.assertRaises(ValueError): normalize_observations([{**BASE,"occurred_at":"2025-08-26T11:00:00"}])
if __name__=="__main__": unittest.main()
