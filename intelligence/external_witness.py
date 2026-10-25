"""EDGE prospective external witness verifier.

A separately collected GitHub commit receipt can attest that a SHA-256 digest
was already present in a committed file. Receipt content is caller supplied;
the verifier does NOT claim external verification until a trusted connector
checks commit existence, author/time and immutable blob bytes separately.
"""
import hashlib
import json
from intelligence.prediction_journal import _dt

def commitment_manifest(commitments):
    if not isinstance(commitments,list) or not commitments:raise ValueError("commitments required")
    ids=set(); hashes=[]
    for r in commitments:
        if not isinstance(r,dict) or r.get("schema")!="edge.learning.forecast_commitment.v1":raise ValueError("invalid commitment")
        pid=r.get("prediction_id")
        if not isinstance(pid,str) or pid in ids:raise ValueError("duplicate commitment")
        ids.add(pid)
        seal=r.get("seal_sha256")
        if not isinstance(seal,str) or len(seal)!=64 or any(c not in "0123456789abcdef" for c in seal):
            raise ValueError("invalid seal")
        contents={k:v for k,v in r.items() if k!="seal_sha256"}
        canonical=json.dumps(contents,ensure_ascii=False,sort_keys=True,separators=(",",":"))
        if hashlib.sha256(canonical.encode()).hexdigest()!=seal:raise ValueError("tampered commitment")
        hashes.append({"prediction_id":pid,"seal_sha256":seal})
    record={"schema":"edge.learning.witness_manifest.v1","commitments":sorted(hashes,key=lambda x:x["prediction_id"])}
    record["manifest_sha256"]=hashlib.sha256(json.dumps(record,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return record

def examine_receipt(manifest,receipt):
    if not isinstance(manifest,dict) or manifest.get("schema")!="edge.learning.witness_manifest.v1":
        raise ValueError("invalid manifest")
    if not isinstance(receipt,dict) or set(receipt)!={"manifest_sha256","commit_sha","commit_timestamp","external_verified"}:
        raise ValueError("invalid receipt")
    if receipt["manifest_sha256"]!=manifest["manifest_sha256"]:raise ValueError("manifest digest mismatch")
    _dt(receipt["commit_timestamp"])
    sha=receipt["commit_sha"]
    if not isinstance(sha,str) or len(sha)!=40 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("invalid commit identifier")
    # No independently fetched receipt = no external proof, regardless of supplied flag.
    return {"schema":"edge.learning.witness_review.v1","manifest_sha256":manifest["manifest_sha256"],
            "receipt_status":"UNVERIFIED_CLAIM","external_timestamp_verified":False,
            "commitment_verified_independently":False,"research_only":True,
            "promotion_authorized":False}
