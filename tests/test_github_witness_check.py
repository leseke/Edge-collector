import base64
import hashlib
import json
import unittest
from intelligence.github_witness_check import verify_public_witness

SHA="a"*40
PATH="witnesses/research.json"
BODY={"schema":"edge.learning.witness_manifest.v1","commitments":[{"prediction_id":"p","seal_sha256":"b"*64}]}
BODY["manifest_sha256"]=hashlib.sha256(json.dumps(BODY,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def fake(url):
 if "/contents/" in url:
  return {"path":PATH,"type":"file","encoding":"base64","content":base64.b64encode(json.dumps(BODY).encode()).decode()}
 return {"sha":SHA,"commit":{"committer":{"date":"2026-01-02T00:00:00Z"}}}
def check(fetch=fake,cutoff="2026-01-03T00:00:00Z"):
 return verify_public_witness(repo="leseke/Edge-collector",commit_sha=SHA,path=PATH,
    expected_manifest_sha256=BODY["manifest_sha256"],cutoff=cutoff,fetch_json=fetch)
class GithubWitnessTests(unittest.TestCase):
 def test_matching_object_not_time_proof(self):
  r=check()
  self.assertTrue(r["repository_object_matches"])
  self.assertFalse(r["independent_early_timestamp_proven"])
  self.assertFalse(r["promotion_authorized"])
 def test_claimed_late_commit(self):
  with self.assertRaises(ValueError):check(cutoff="2026-01-01T00:00:00Z")
 def test_mismatch_detected(self):
  def altered(url):
   response=fake(url)
   if "/contents/" in url:
    other={**BODY,"manifest_sha256":"0"*64}
    response["content"]=base64.b64encode(json.dumps(other).encode()).decode()
   return response
  with self.assertRaises(ValueError):check(fetch=altered)
 def test_unapproved_repository_denied(self):
  with self.assertRaises(ValueError):
   verify_public_witness(repo="another/repo",commit_sha=SHA,path=PATH,
     expected_manifest_sha256=BODY["manifest_sha256"],cutoff="2026-01-03T00:00:00Z",fetch_json=fake)
if __name__=="__main__":unittest.main()
