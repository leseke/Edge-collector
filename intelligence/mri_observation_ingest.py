"""Safely ingest explicitly supplied public MRI signals into a research-only candidate feed.

This is not an autonomous source fetcher. No network, no purchases, no secrets.
The caller supplies independently collected public observations.
"""
import json
from pathlib import Path
from datetime import datetime

ALLOWED={"id","subject","actor","action","occurred_at","observed_at","source_url","summary"}
def _time(v):
    d=datetime.fromisoformat(v.replace("Z","+00:00"))
    if d.tzinfo is None: raise ValueError("timezone required")
    return d

def normalize_observations(records):
    if not isinstance(records,list): raise ValueError("records list required")
    output=[]
    ids=set()
    for r in records:
        if not isinstance(r,dict) or set(r)!=ALLOWED: raise ValueError("strict public observation fields required")
        if not all(isinstance(r[k],str) and 0<len(r[k])<2000 for k in ALLOWED):
            raise ValueError("invalid observation text")
        if not r["source_url"].startswith("https://"):
            raise ValueError("HTTPS public source required")
        if r["id"] in ids: raise ValueError("duplicate observation")
        ids.add(r["id"])
        if _time(r["observed_at"])<_time(r["occurred_at"]):
            raise ValueError("observation cannot precede event")
        output.append(dict(r))
    return sorted(output,key=lambda r:(r["observed_at"],r["id"]))

def create_research_digest(records):
    observations=normalize_observations(records)
    return {"schema":"edge.mri.observations.review.v1",
            "status":"RESEARCH_ONLY",
            "review_required":True,
            "decision":"NOT_EVALUATED",
            "count":len(observations),
            "observations":observations}

def prepare_digest(input_path,output_path):
    data=json.loads(Path(input_path).read_text(encoding="utf-8"))
    if not isinstance(data,dict) or set(data)!={"schema","observations"} or data["schema"]!="edge.mri.observations.input.v1":
        raise ValueError("unexpected input schema")
    digest=create_research_digest(data["observations"])
    target=Path(output_path)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(digest,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return digest
