"""Private prospective commitment ledger, tamper-evident and append-only.

Storage is local JSONL; integrity protects against accidental edits, not a
malicious administrator. Neither forecasts nor outcomes authorize trades.
"""
import hashlib
import json
from pathlib import Path
from intelligence.prediction_journal import _dt, _records

def canonical(x):
    return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"))

def seal_forecast(path,*,prediction,baseline_positive,challenger_positive,committed_at,evidence_hashes):
    if not isinstance(prediction,dict) or prediction.get("type")!="PREDICTION":raise ValueError("prediction required")
    if any(type(v) is not bool for v in (baseline_positive,challenger_positive)):raise ValueError("boolean forecasts required")
    if _dt(committed_at)>_dt(prediction["as_of"]):raise ValueError("late forecast")
    if not isinstance(evidence_hashes,dict) or not evidence_hashes or any(not isinstance(k,str) or not isinstance(v,str) or len(v)!=64 or any(x not in "0123456789abcdef" for x in v) for k,v in evidence_hashes.items()):
        raise ValueError("evidence SHA-256 required")
    if set(evidence_hashes)!=set(prediction["evidence_ids"]):raise ValueError("evidence ids mismatch")
    record={"schema":"edge.learning.forecast_commitment.v1","prediction_id":prediction["id"],"committed_at":committed_at,
            "baseline_positive":baseline_positive,"challenger_positive":challenger_positive,
            "evidence_sha256":dict(sorted(evidence_hashes.items())),"execution_authorized":False}
    record["seal_sha256"]=hashlib.sha256(canonical(record).encode()).hexdigest()
    p=Path(path)
    existing=_records(path)
    for prior in existing:
        if prior.get("prediction_id")==prediction["id"]:
            if prior==record:return record
            raise ValueError("prediction already committed")
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("a",encoding="utf-8") as f:f.write(canonical(record)+"\n")
    return record

def verified_commitments(path,predictions):
    result=[]
    for r in _records(path):
        if r.get("schema")!="edge.learning.forecast_commitment.v1":raise ValueError("unknown ledger entry")
        sealed={k:v for k,v in r.items() if k!="seal_sha256"}
        if hashlib.sha256(canonical(sealed).encode()).hexdigest()!=r.get("seal_sha256"):
            raise ValueError("commitment integrity mismatch")
        prediction=predictions.get(r["prediction_id"])
        if not prediction or _dt(r["committed_at"])>_dt(prediction["as_of"]):
            raise ValueError("unrecognized or late commitment")
        if set(r["evidence_sha256"])!=set(prediction["evidence_ids"]):
            raise ValueError("evidence mismatches")
        result.append({"prediction_id":r["prediction_id"],"forecast_at":r["committed_at"],
                       "baseline_positive":r["baseline_positive"],"challenger_positive":r["challenger_positive"]})
    if len({x["prediction_id"] for x in result})!=len(result):raise ValueError("duplicate commitments")
    return result
