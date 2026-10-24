import tempfile
import json
import unittest
from pathlib import Path
from intelligence.mri_public_adapter import build_public_cases, publish_reviewed_cases

ITEM={"case_id":"pk-cn-2022","label":"Pokémon Chine","as_of":"2022-09-21T23:59:59+08:00",
"thesis":"Participation durable possible","rival":"Intérêt passager possible",
"limitations":"Capture contemporaine absente","source_urls":["https://www.pokemon.cn/tcg/product/16380.html"]}
GATE={"case_id":"pk-cn-2022","replay_ready":False,"financial_signal":"NOT_EVALUATED"}

class MriPublicAdapterTests(unittest.TestCase):
 def test_research_only(self):
  self.assertEqual(build_public_cases([ITEM],[GATE])[0]["state"],"RESEARCH_ONLY")
 def test_export_roundtrip(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"data.json"
   publish_reviewed_cases([ITEM],[GATE],p)
   self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["cases"][0]["case_id"],ITEM["case_id"])
 def test_cannot_publish_capital(self):
  with self.assertRaises(ValueError):
   build_public_cases([{**ITEM,"capital":300}],[GATE])
 def test_cannot_publish_buy_signal(self):
  with self.assertRaises(ValueError):
   build_public_cases([ITEM],[{**GATE,"financial_signal":"BUY"}])
 def test_no_unqualified_future_case(self):
  with self.assertRaises(ValueError):
   build_public_cases([ITEM],[{**GATE,"replay_ready":True}])
 def test_missing_gate(self):
  with self.assertRaises(ValueError):
   build_public_cases([ITEM],[])
 def test_duplicate_gates(self):
  with self.assertRaises(ValueError):
   build_public_cases([ITEM],[GATE,GATE])
if __name__=="__main__": unittest.main()
