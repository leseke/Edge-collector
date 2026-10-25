"""Read-only GitHub witness check for already published public manifests.

Never pushes content. Git commit dates can be authored/backdated: a matching
repository object is NOT independent proof of when GitHub first received it.
"""
import hashlib
import json
import re
from datetime import timezone
from intelligence.prediction_journal import _dt

SHA40=re.compile(r"^[0-9a-f]{40}$")
def _json_bytes(obj):
    return json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode("utf-8")

def verify_public_witness(*,repo,commit_sha,path,expected_manifest_sha256,cutoff,fetch_json=None):
    if repo!="leseke/Edge-collector" or not isinstance(commit_sha,str) or not SHA40.fullmatch(commit_sha):
        raise ValueError("fixed repository and exact commit required")
    if not isinstance(path,str) or not path.startswith("witnesses/") or ".." in path or not path.endswith(".json"):
        raise ValueError("public witness path only")
    if not isinstance(expected_manifest_sha256,str) or not re.fullmatch(r"[0-9a-f]{64}",expected_manifest_sha256):
        raise ValueError("expected digest required")
    limit=_dt(cutoff)
    if fetch_json is None:
        import urllib.request
        def fetch_json(url):
            request=urllib.request.Request(url,headers={"Accept":"application/vnd.github+json","User-Agent":"EDGE-witness-verifier"})
            with urllib.request.urlopen(request,timeout=10) as response:
                if response.geturl()!=url:raise ValueError("redirect denied")
                return json.loads(response.read(500000))
    base="https://api.github.com/repos/leseke/Edge-collector"
    commit=fetch_json(f"{base}/commits/{commit_sha}")
    blob=fetch_json(f"{base}/contents/{path}?ref={commit_sha}")
    if commit.get("sha")!=commit_sha:raise ValueError("commit mismatch")
    if blob.get("path")!=path or blob.get("type")!="file" or blob.get("encoding")!="base64":
        raise ValueError("unexpected content response")
    import base64
    body=base64.b64decode(blob["content"],validate=False)
    if len(body)>100000:raise ValueError("witness too large")
    manifest=json.loads(body)
    if manifest.get("schema")!="edge.learning.witness_manifest.v1":
        raise ValueError("unexpected witness schema")
    supplied=manifest.get("manifest_sha256")
    unsigned={k:v for k,v in manifest.items() if k!="manifest_sha256"}
    recalculated=hashlib.sha256(_json_bytes(unsigned)).hexdigest()
    if supplied!=recalculated or supplied!=expected_manifest_sha256:
        raise ValueError("witness digest mismatch")
    timestamp=commit.get("commit",{}).get("committer",{}).get("date")
    if not timestamp or _dt(timestamp)>limit:raise ValueError("commit claimed date outside cutoff")
    return {"schema":"edge.learning.github_witness_check.v1",
            "repository_object_matches":True,"manifest_sha256":recalculated,
            "commit_sha":commit_sha,"commit_date_claim":timestamp,
            "github_receipt_time_verified":False,
            "independent_early_timestamp_proven":False,
            "status":"MATCHING_GITHUB_OBJECT_NOT_TIME_PROOF",
            "promotion_authorized":False,"investment_policy_changed":False}
