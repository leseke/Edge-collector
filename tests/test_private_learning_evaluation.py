import unittest
from intelligence.private_learning_evaluation import evaluate_private_batch
def cases(n,improve=False):
 return [{"case_id":str(i),"baseline_correct":False,"challenger_correct":improve,"outcome_observed":True} for i in range(n)]
class PrivateLearningTests(unittest.TestCase):
 def test_positive_gain_requires_review(self):
  x=evaluate_private_batch(cases(30,True))
  self.assertEqual(x["status"],"REVIEW_REQUIRED")
  self.assertEqual(x["ui_visibility"],"INTERNAL_ONLY")
  self.assertFalse(x["promotion_authorized"])
 def test_low_sample_not_evidence(self):
  self.assertEqual(evaluate_private_batch(cases(29,True))["status"],"INSUFFICIENT_EVIDENCE")
 def test_no_gain(self):
  self.assertEqual(evaluate_private_batch(cases(30))["status"],"NO_DEMONSTRATED_GAIN")
 def test_no_future_outcome(self):
  x=cases(30,True);x[0]["outcome_observed"]=False
  with self.assertRaises(ValueError):evaluate_private_batch(x)
 def test_duplicates_rejected(self):
  x=cases(30,True);x[-1]["case_id"]="0"
  with self.assertRaises(ValueError):evaluate_private_batch(x)
 def test_invalid_types_rejected(self):
  x=cases(30,True);x[0]["challenger_correct"]=1
  with self.assertRaises(ValueError):evaluate_private_batch(x)
if __name__=="__main__":unittest.main()
