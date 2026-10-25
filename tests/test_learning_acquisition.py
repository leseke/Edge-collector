import unittest
from intelligence.learning_acquisition import intake_public_study,compare_candidate_on_holdout
from intelligence.learning_intelligence import propose_lesson
P=dict(source_url="https://example.org/study",published_at="2026-10-20T08:00:00Z",observed_at="2026-10-25T08:00:00Z",title="Markets and liquidity",text="Market liquidity and retail inventory cycle evidence. "*100)
class AcquisitionTests(unittest.TestCase):
 def test_intake_is_unreviewed(self):
  x=intake_public_study(**P)
  self.assertEqual(x["status"],"UNREVIEWED_SOURCE")
  self.assertIn("liquidity",x["candidate_topics"])
  self.assertFalse(x["lesson_generated"])
  self.assertFalse(x["knowledge_adopted"])
 def test_change_at_end_changes_hash(self):
  a=intake_public_study(**P)
  b=intake_public_study(**{**P,"text":P["text"]+" NEW finding at document end"})
  self.assertNotEqual(a["text_sha256"],b["text_sha256"])
 def test_future_source_rejected(self):
  with self.assertRaises(ValueError):intake_public_study(**{**P,"published_at":"2026-10-26T08:00:00Z"})
 def test_oversized_is_not_silently_truncated(self):
  with self.assertRaises(ValueError):intake_public_study(**{**P,"text":"A"*200001})
 def test_evaluation_does_not_auto_adopt(self):
  lesson=propose_lesson(topic="liquidity",claim="Turnover cannot be inferred from asking prices.",example="Active listings can sit for weeks.",limitations="Incomplete sale records make inference difficult.",source_url=P["source_url"],observed_at=P["observed_at"],source_published_at=P["published_at"])
  x=compare_candidate_on_holdout(lesson,[False]*25,[True]*25)
  self.assertFalse(x["prospective_validation_established"])
  self.assertFalse(x["automatically_promoted"])
if __name__=="__main__":unittest.main()
