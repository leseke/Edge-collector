"""Private append-only retail observation journal with deterministic replay.

A stored retailer observation is a source claim, not an authenticated sale.
History uses bounded JSONL, stable content hashes and conflicts fail closed.
"""
import hashlib
import json
from pathlib import Path
from intelligence.prediction_journal import _dt
from intelligence.retail_transition_engine import detect_retail_transitions
from intelligence.retail_signal_confirmation import confirm_retail_signals

MAX_ROWS=5000
def _canonical(obj):
    return json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False)
def _read(path):
    p=Path(path)
    if not p.exists():return []
    if p.stat().st_size>8_000_000:raise ValueError("journal exceeds byte limit")
    rows=[json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows)>MAX_ROWS:raise ValueError("journal exceeds row limit")
    for entry in rows:
        if entry.get("schema")!="edge.retail.history.v1" or entry.get("id")!=hashlib.sha256(_canonical(entry.get("observation")).encode()).hexdigest():
            raise ValueError("corrupt observation journal")
    return rows

def append_retail_observation(path,row):
    if not isinstance(row,dict) or row.get("schema")!="edge.retail.observation.v1":
        raise ValueError("normalized observation required")
    if any(row.get(k) is not False for k in ("purchase_authorized","completed_sale_evidence","event_confirmed","investment_recommendation")):
        raise ValueError("unsafe observation")
    _dt(row["observed_at"])
    p=Path(path)
    existing=_read(p)
    ident=hashlib.sha256(_canonical(row).encode()).hexdigest()
    if any(x["id"]==ident for x in existing):return {"id":ident,"appended":False}
    for entry in existing:
        old=entry["observation"]
        if all(old[k]==row[k] for k in ("source_id","seller","product_key","vertical","observed_at")):
            raise ValueError("conflicting observation at same timestamp")
    if len(existing)>=MAX_ROWS:raise ValueError("journal full")
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("a",encoding="utf-8") as out:
        out.write(_canonical({"schema":"edge.retail.history.v1","id":ident,"observation":row})+"\n")
    return {"id":ident,"appended":True}

def summarize_retail_history(path,*,as_of):
    cutoff=_dt(as_of)
    rows=[x["observation"] for x in _read(path) if _dt(x["observation"]["observed_at"])<=cutoff]
    transitions=detect_retail_transitions(rows)
    signals=confirm_retail_signals(rows)
    confirmed=sum(x["status"]=="SOURCE_RECONFIRMED" for x in signals)
    return {"schema":"edge.retail.quality.v1","internal_only":True,
        "as_of":as_of,"observations":len(rows),"candidate_events":len(transitions),
        "source_reconfirmed":confirmed,"unconfirmed":len(signals)-confirmed,
        "false_positive_rate":None,"false_positive_rate_status":"NO_INDEPENDENT_GROUND_TRUTH",
        "financial_roi_measured":False,"verified_completed_sales":0,
        "purchase_authorized":False}
