"""EDGE Learning Library V1: append-only, source-grounded knowledge records.

Never executes source instructions or automatically alters strategies or policies.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from intelligence.learning_intelligence import _time, ALLOWED_TOPICS

def _canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":"))

def _read(path):
    p=Path(path)
    if not p.exists():return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]

def register_lesson(path,lesson,*,revision_of=None):
    required={"schema","topic","claim","example","limitations","source_url","source_published_at","observed_at","status","eligible_for_decisions","changes_permissions","changes_investment_policy","id"}
    if not isinstance(lesson,dict) or set(lesson)!=required or lesson["schema"]!="edge.learning.lesson.v1":
        raise ValueError("invalid lesson schema")
    if lesson["topic"] not in ALLOWED_TOPICS or lesson["status"]!="CANDIDATE" or any(lesson[k] is not False for k in ("eligible_for_decisions","changes_permissions","changes_investment_policy")):
        raise ValueError("unsafe lesson")
    if not isinstance(lesson["source_url"],str) or not lesson["source_url"].startswith("https://"):
        raise ValueError("source required")
    if _time(lesson["source_published_at"])>_time(lesson["observed_at"]):
        raise ValueError("future evidence")
    fields={k:v for k,v in lesson.items() if k!="id"}
    expected=hashlib.sha256(_canonical(fields).encode()).hexdigest()[:24]
    if lesson["id"]!=expected:raise ValueError("lesson signature mismatch")
    existing=_read(path)
    previous={x["lesson"]["id"] for x in existing}
    if revision_of is not None and revision_of not in previous:
        raise ValueError("unknown revision predecessor")
    if any(x["lesson"]["id"]==lesson["id"] for x in existing):
        if revision_of is not None:raise ValueError("already registered revision")
        return lesson["id"]
    entry={"schema":"edge.learning.library_entry.v1","lesson":lesson,"revision_of":revision_of,
           "library_status":"PENDING_REVIEW","policy_change_authorized":False}
    dest=Path(path);dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("a",encoding="utf-8") as f:f.write(_canonical(entry)+"\n")
    return lesson["id"]

def library_summary(path,*,as_of):
    cutoff=_time(as_of)
    visible=[x for x in _read(path) if _time(x["lesson"]["observed_at"])<=cutoff]
    counts={topic:sum(x["lesson"]["topic"]==topic for x in visible) for topic in sorted(ALLOWED_TOPICS)}
    return {"schema":"edge.learning.library_summary.v1","as_of":as_of,
            "total":len(visible),"by_topic":counts,
            "latest_observed_at":max((x["lesson"]["observed_at"] for x in visible),default=None),
            "all_pending_review":all(x["library_status"]=="PENDING_REVIEW" for x in visible)}
