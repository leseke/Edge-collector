import tempfile
import unittest
from pathlib import Path
from intelligence.learning_intelligence import propose_lesson
from intelligence.learning_library import register_lesson,library_summary,_read
P=dict(topic="pricing",claim="Asking prices alone do not prove completed transaction value.",source_url="https://example.org/study",observed_at="2026-10-25T09:00:00Z",source_published_at="2026-10-24T09:00:00Z",example="Offers can remain unsold for months even with high asking prices.",limitations="Observations lack complete sales coverage.")
class LibraryTests(unittest.TestCase):
 def test_register_and_idempotence(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/"learn.jsonl";lesson=propose_lesson(**P)
   register_lesson(path,lesson);register_lesson(path,lesson)
   self.assertEqual(len(_read(path)),1)
   self.assertEqual(library_summary(path,as_of="2026-10-26T00:00:00Z")["total"],1)
 def test_revision_retains_predecessor(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/"learn.jsonl";a=propose_lesson(**P);b=propose_lesson(**{**P,"claim":"An asking price does not prove the amount paid by buyers."})
   register_lesson(path,a);register_lesson(path,b,revision_of=a["id"])
   self.assertEqual(_read(path)[1]["revision_of"],a["id"])
 def test_future_is_excluded_from_historical_view(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/"learn.jsonl";register_lesson(path,propose_lesson(**P))
   self.assertEqual(library_summary(path,as_of="2026-10-24T00:00:00Z")["total"],0)
 def test_tampering_fails(self):
  with tempfile.TemporaryDirectory() as d:
   a=propose_lesson(**P);a["claim"]="Unexpected changes"
   with self.assertRaises(ValueError):register_lesson(Path(d)/"l",a)
 def test_unknown_predecessor_fails(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):register_lesson(Path(d)/"l",propose_lesson(**P),revision_of="missing")
if __name__=="__main__":unittest.main()
