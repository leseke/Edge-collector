import unittest
from intelligence.learning_intelligence import propose_lesson,evaluate_lesson
P=dict(topic="liquidity",claim="Median sold price alone does not estimate turnover.",
source_url="https://example.org/market",observed_at="2026-10-25T10:00:00Z",
source_published_at="2026-10-24T10:00:00Z",
example="Two observed sales cannot reveal total market volume.",
limitations="Sample selection and missing listings prevent strong inference.")
class LearningTests(unittest.TestCase):
 def test_candidate_cannot_change_policy(self):
  x=propose_lesson(**P);self.assertEqual(x["status"],"CANDIDATE")
  self.assertFalse(x["changes_investment_policy"]);self.assertFalse(x["eligible_for_decisions"])
 def test_future_source_rejected(self):
  with self.assertRaises(ValueError):propose_lesson(**{**P,"source_published_at":"2026-10-26T10:00:00Z"})
 def test_out_of_scope_topic_rejected(self):
  with self.assertRaises(ValueError):propose_lesson(**{**P,"topic":"security_policy"})
 def test_no_promotion_without_examples(self):
  d=evaluate_lesson(propose_lesson(**P),baseline_cases=[False],challenger_cases=[True])
  self.assertEqual(d["status"],"INSUFFICIENT_EVIDENCE")
 def test_gain_still_requires_review(self):
  d=evaluate_lesson(propose_lesson(**P),baseline_cases=[False]*25,challenger_cases=[True]*25)
  self.assertEqual(d["status"],"REVIEW_REQUIRED");self.assertFalse(d["automatically_promoted"])
 def test_no_gain_is_not_promoted(self):
  d=evaluate_lesson(propose_lesson(**P),baseline_cases=[True]*25,challenger_cases=[False]*25)
  self.assertEqual(d["status"],"NO_DEMONSTRATED_GAIN")
 def test_falsified_inputs_rejected(self):
  with self.assertRaises(ValueError):evaluate_lesson(propose_lesson(**P),baseline_cases=[1]*25,challenger_cases=[True]*25)
if __name__=="__main__":unittest.main()
