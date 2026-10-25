import hashlib
import unittest
from intelligence.mri_evidence_segments import segment_page

class SegmentTests(unittest.TestCase):
 def test_full_coverage_long_page(self):
  text=("Pokémon launch observation. "*600)+"FINAL IMPORTANT RETIREMENT SIGNAL."
  d=segment_page("pokemon","https://www.pokemon.com", "<html>"+text+"</html>")
  self.assertTrue(d["complete"])
  self.assertGreater(len(d["segments"]),3)
  restored="".join(p["text"] for p in d["segments"])
  self.assertEqual(restored,text)
  self.assertIn("RETIREMENT SIGNAL",d["segments"][-1]["text"])
  self.assertEqual(hashlib.sha256(restored.encode()).hexdigest(),d["source_sha256"])
 def test_contiguous_positions(self):
  d=segment_page("lego","https://www.lego.com","<p>"+"A"*5000+"</p>",max_chars=500)
  self.assertEqual(d["segments"][0]["start"],0)
  self.assertEqual(d["segments"][-1]["end"],5000)
  self.assertTrue(all(a["end"]==b["start"] for a,b in zip(d["segments"],d["segments"][1:])))
 def test_oversized_rejected(self):
  with self.assertRaises(ValueError):segment_page("x","https://example.org","A"*2000001)
 def test_invalid_chunk_size(self):
  with self.assertRaises(ValueError):segment_page("x","https://example.org","A"*1000,max_chars=20)
if __name__=="__main__":unittest.main()
