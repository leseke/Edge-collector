"""Append-only research journal of observed BrickLink price guides.

Stores aggregates, not individual transactions. Identical snapshots deduplicated.
No live API calls, trades, deployment or source-secret retention.
"""
import hashlib
import json
from pathlib import Path
from intelligence.prediction_journal import _dt

def append_observation(path, observation):
    if not isinstance(observation,dict) or observation.get("schema")!="edge.market.bricklink_sold_aggregate.v1":
        raise ValueError("sold aggregate required")
    if observation.get("outcome_learning_eligible") is not False or observation.get("purchase_authorized") is not False:
        raise ValueError("unsafe evidence classification")
    observed=_dt(observation["observed_at"])
    for key in ("set_no","condition","currency","source_payload_sha256"):
        if not isinstance(observation.get(key),str) or not observation[key]:
            raise ValueError("missing market dimension")
    record={"schema":"edge.market.observation_journal.v1","observation":observation,
            "learning_status":"UNVERIFIED_AGGREGATE"}
    record["id"]=hashlib.sha256(json.dumps(record,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
    p=Path(path)
    existing=[json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()] if p.exists() else []
    if any(x.get("id")==record["id"] for x in existing):return record
    for x in existing:
        o=x["observation"]
        if all(o[k]==observation[k] for k in ("set_no","condition","currency","observed_at")):
            raise ValueError("conflicting observation for same timestamp")
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("a",encoding="utf-8") as f:
        f.write(json.dumps(record,sort_keys=True,ensure_ascii=False,separators=(",",":"))+"\n")
    return record
