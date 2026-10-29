"""Read-only evidence snapshot intake for resale research.

A snapshot verifies bytes observed, not transaction authenticity.
No network requests, no paid API and no permission to publish or buy.
"""
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
from intelligence.sales_source_typing import classify_sales_observations

MAX_BYTES=200000
def archive_snapshot(*,source_url,record_type,product_key,amount_eur,observed_at,evidence_id,source_bytes):
    u=urlsplit(source_url)
    if u.scheme!="https" or not u.hostname or u.username or u.password or u.fragment:
        raise ValueError("HTTPS evidence URL required")
    if not isinstance(source_bytes,bytes) or not 20<=len(source_bytes)<=MAX_BYTES:
        raise ValueError("snapshot size invalid")
    digest=hashlib.sha256(source_bytes).hexdigest()
    row={"evidence_id":evidence_id,"record_type":record_type,"product_key":product_key,
        "source_url":source_url,"observed_at":observed_at,"amount_eur":amount_eur,
        "proof_sha256":digest}
    classified=classify_sales_observations([row],as_of=observed_at)
    return {"schema":"edge.learning.snapshot.v1","evidence":row,
            "byte_size":len(source_bytes),"source_authenticity":"UNVERIFIED",
            "sale_verified":False,"classification":classified["counts"],
            "transaction_not_proven":True,"purchase_authorized":False}

def stage_snapshot_file(input_json, source_file, output_json):
    metadata=json.loads(Path(input_json).read_text(encoding="utf-8"))
    if not isinstance(metadata,dict) or set(metadata)!={"source_url","record_type","product_key","amount_eur","observed_at","evidence_id"}:
        raise ValueError("strict input fields required")
    path=Path(source_file)
    if path.stat().st_size>MAX_BYTES:raise ValueError("oversized evidence")
    result=archive_snapshot(**metadata,source_bytes=path.read_bytes())
    target=Path(output_json);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,sort_keys=True,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result
