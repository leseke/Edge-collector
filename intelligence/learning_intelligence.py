"""EDGE Learning Intelligence V1: evidence-gated analytical playbook.

Updates analytical heuristics only; never modifies investment rules, capital,
connectors, code, prompts, security policy, or executes external instructions.
"""
import hashlib
import json
from datetime import datetime,timezone

ALLOWED_TOPICS={"market_microstructure","pricing","liquidity","consumer_behavior","supply_cycles","retail","resale","commerce"}
def _time(x):
    if not isinstance(x,str):raise ValueError("timestamp required")
    d=datetime.fromisoformat(x.replace("Z","+00:00"))
    if d.tzinfo is None:raise ValueError("timezone required")
    return d.astimezone(timezone.utc)
def propose_lesson(*,topic,claim,source_url,observed_at,source_published_at,example,limitations):
    if topic not in ALLOWED_TOPICS:raise ValueError("topic not allowed")
    if not isinstance(source_url,str) or not source_url.startswith("https://"):raise ValueError("HTTPS provenance required")
    if _time(source_published_at)>_time(observed_at):raise ValueError("future published content")
    for v in (claim,example,limitations):
        if not isinstance(v,str) or not 10<=len(v.strip())<=1200:raise ValueError("substantive bounded text required")
    record={"schema":"edge.learning.lesson.v1","topic":topic,"claim":claim.strip(),
        "example":example.strip(),"limitations":limitations.strip(),
        "source_url":source_url,"source_published_at":source_published_at,
        "observed_at":observed_at,"status":"CANDIDATE","eligible_for_decisions":False,
        "changes_permissions":False,"changes_investment_policy":False}
    record["id"]=hashlib.sha256(json.dumps(record,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
    return record

def evaluate_lesson(lesson,*,baseline_cases,challenger_cases,minimum_cases=20):
    if not isinstance(lesson,dict) or lesson.get("schema")!="edge.learning.lesson.v1" or lesson.get("status")!="CANDIDATE":
        raise ValueError("candidate lesson required")
    if type(minimum_cases) is not int or minimum_cases<20:raise ValueError("minimum cases too low")
    for data in (baseline_cases,challenger_cases):
        if not isinstance(data,list) or any(type(x) is not bool for x in data):raise ValueError("boolean held-out evaluations required")
    if len(baseline_cases)!=len(challenger_cases) or len(baseline_cases)<minimum_cases:
        status="INSUFFICIENT_EVIDENCE"
    else:
        gains=sum(challenger_cases)-sum(baseline_cases)
        status="REVIEW_REQUIRED" if gains>0 else "NO_DEMONSTRATED_GAIN"
    return {"schema":"edge.learning.evaluation.v1","lesson_id":lesson["id"],
       "cases":len(baseline_cases),"baseline_correct":sum(baseline_cases),
       "challenger_correct":sum(challenger_cases),"status":status,
       "automatically_promoted":False,"eligible_for_decisions":False,
       "changes_investment_policy":False}
