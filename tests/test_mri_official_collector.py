import json
import tempfile
import unittest
from pathlib import Path
from intelligence.mri_official_collector import SOURCES, observe, collect

PAGE="<html><title>Official news</title><h1>Official Pokémon product update released for collectors</h1><script>secret-token-value</script></html>"
T="2026-10-25T09:00:00+00:00"
class OfficialCollectorTests(unittest.TestCase):
 def test_source_list_is_official_and_fixed(self):
  self.assertEqual(len(SOURCES),2)
  self.assertTrue(all(s[1].startswith(("https://www.pokemon.com/","https://www.lego.com/")) for s in SOURCES))
 def test_real_observed_time_no_fake_publication(self):
  o=observe(SOURCES[0],PAGE,T)
  self.assertEqual(o["occurred_at"],T)
  self.assertEqual(o["observed_at"],T)
  self.assertNotIn("secret-token-value",o["summary"])
 def test_stable_identity(self):
  self.assertEqual(observe(SOURCES[0],PAGE,T)["id"],observe(SOURCES[0],PAGE,T)["id"])
 def test_no_network_in_injected_fixture(self):
  with tempfile.TemporaryDirectory() as d:
   v=collect(Path(d)/"out.json",fetcher=lambda u:PAGE,now=T)
   self.assertEqual(v["count"],2)
   self.assertEqual(v["collection_status"],"OK")
   self.assertEqual(v["decision"],"NOT_EVALUATED")
 def test_partial_failure_fails_not_silently(self):
  with tempfile.TemporaryDirectory() as d:
   def f(u):
    if "lego" in u:raise TimeoutError("test")
    return PAGE
   v=collect(Path(d)/"out.json",fetcher=f,now=T)
   self.assertEqual(v["collection_status"],"PARTIAL")
   self.assertEqual(v["source_failures"][0]["error_type"],"TimeoutError")
 def test_zero_sources_returns_failed(self):
  with tempfile.TemporaryDirectory() as d:
   v=collect(Path(d)/"out.json",fetcher=lambda _: (_ for _ in ()).throw(TimeoutError()),now=T)
   self.assertEqual(v["collection_status"],"FAILED")
   self.assertEqual(v["count"],0)
 def test_reject_large_page(self):
  with self.assertRaises(ValueError):observe(SOURCES[0],"A"*300000,T)
if __name__=="__main__":unittest.main()
