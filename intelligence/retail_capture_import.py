"""Import manually reviewed public retail captures into the EDGE research journal.

Accepts structured observations only; cannot infer sales, verify stock, or fetch
websites. Source documents must be externally captured and reviewed.
"""
import hashlib
from intelligence.retail_radar import normalize_offer
from intelligence.retail_observation_history import append_retail_observation

def import_reviewed_capture(*,journal_path,capture,as_of,snapshot_bytes):
    from intelligence.prediction_journal import _dt
    if not isinstance(capture,dict):
        raise ValueError("capture must be a mapping")
    keys={"source_id","source_domain","listing_url","actual_seller","product_key",
          "vertical","offer_state","observed_at","price_eur","source_snapshot_sha256"}
    if set(capture)!=keys:raise ValueError("strict capture fields required")
    sha=capture["source_snapshot_sha256"]
    if not isinstance(sha,str) or len(sha)!=64 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("snapshot digest required")
    if not isinstance(snapshot_bytes,bytes) or not 20<=len(snapshot_bytes)<=200000:\n        raise ValueError("bounded source snapshot bytes required")\n    if hashlib.sha256(snapshot_bytes).hexdigest()!=sha:\n        raise ValueError("snapshot fingerprint mismatch")\n    if _dt(capture["observed_at"])>_dt(as_of):raise ValueError("future observation")
    row=normalize_offer(**{k:v for k,v in capture.items() if k!="source_snapshot_sha256"})
    row["source_snapshot_sha256"]=sha\n    row["source_snapshot_authenticated"]=False\n    result=append_retail_observation(journal_path,row)
    return {"schema":"edge.retail.manual_capture_import.v1",
        "journal_id":result["id"],"appended":result["appended"],
        "source_snapshot_sha256":sha,"source_snapshot_authenticated":False,
        "source_stock_verified":False,"completed_sale_verified":False,
        "research_only":True,"purchase_authorized":False}
