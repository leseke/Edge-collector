"""EDGE Prediction Journal V1 — immutable, prospective, research-only predictions.

Append-only JSON Lines with idempotent predictions and as-of evidence cutoff.
No network, purchases, implied probabilities, or retroactive editing.
"""
import hashlib
import json
from datetime import datetime,timezone,timedelta
from pathlib import Path

HORIZONS=(30,90,180,365)
OUTCOMES={"POSITIVE","NEGATIVE","INCONCLUSIVE","NO_DATA"}
def _dt(t):
    if not isinstance(t,str):raise ValueError("timestamp required")
    d=datetime.fromisoformat(t.replace("Z","+00:00"))
    if d.tzinfo is None:raise ValueError("timezone required")
    return d.astimezone(timezone.utc)
def _canon(o):return json.dumps(o,sort_keys=True,ensure_ascii=False,separators=(",",":"))
def _records(path):
    p=Path(path)
    if not p.exists():return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def _append(path,record):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("a",encoding="utf-8") as f:f.write(_canon(record)+"\n")
def create_prediction(path,*,product_key,thesis,rival,as_of,evidence_ids,horizon_days,criterion):
    stamp=_dt(as_of)
    if horizon_days not in HORIZONS or type(horizon_days) is not int:raise ValueError("unsupported horizon")
    for text in (product_key,thesis,rival,criterion):
        if not isinstance(text,str) or not 1<=len(text.strip())<=1000:raise ValueError("invalid text")
    if thesis==rival or not isinstance(evidence_ids,list) or not evidence_ids or len(set(evidence_ids))!=len(evidence_ids) or any(not isinstance(x,str) or not x.strip() for x in evidence_ids):
        raise ValueError("competing thesis and evidence required")
    record={"type":"PREDICTION","schema":"edge.prediction.journal.v1",
            "product_key":product_key,"thesis":thesis,"rival":rival,"as_of":as_of,
            "evidence_ids":sorted(evidence_ids),"horizon_days":horizon_days,
            "due_at":(stamp+timedelta(days=horizon_days)).isoformat(),
            "criterion":criterion,"decision":"NOT_EVALUATED","execution_authorized":False}
    record["id"]=hashlib.sha256(_canon(record).encode()).hexdigest()[:24]
    existing=_records(path)
    if any(x.get("id")==record["id"] for x in existing):return record
    _append(path,record);return record

def append_outcome(path,*,prediction_id,observed_at,outcome,evidence_ids,note):
    stamp=_dt(observed_at)
    existing=_records(path)
    prediction=next((x for x in existing if x.get("type")=="PREDICTION" and x.get("id")==prediction_id),None)
    if prediction is None:raise ValueError("prediction not found")
    if stamp<_dt(prediction["due_at"]):raise ValueError("assessment before horizon")
    if outcome not in OUTCOMES or not isinstance(note,str) or not 1<=len(note)<=1000:raise ValueError("invalid assessment")
    if not isinstance(evidence_ids,list) or (outcome!="NO_DATA" and not evidence_ids) or any(not isinstance(i,str) or not i for i in evidence_ids):
        raise ValueError("outcome evidence required")
    if any(x.get("type")=="OUTCOME" and x.get("prediction_id")==prediction_id for x in existing):
        raise ValueError("outcome already recorded; corrections require separate version")
    result={"type":"OUTCOME","schema":"edge.prediction.outcome.v1","prediction_id":prediction_id,
            "observed_at":observed_at,"outcome":outcome,"evidence_ids":sorted(evidence_ids),
            "note":note,"decision":"NOT_EVALUATED"}
    _append(path,result);return result
