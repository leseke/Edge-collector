"""EDGE learning acquisition: bounded source packets, not self-modifying instructions.

Read-only ingestion of independently obtained texts; publication date required.
Outputs candidate knowledge questions, NOT fabricated lessons or adopted policy.
"""
import hashlib
import json
import re
from intelligence.learning_intelligence import _time

MAX_TEXT=200000
TOPIC_TERMS={
 "pricing":("pricing","price discrimination","tarification","formation des prix"),
 "liquidity":("liquidity","liquidité","turnover","sell-through"),
 "consumer_behavior":("consumer behavior","comportement du consommateur","purchase intention"),
 "supply_cycles":("supply chain","réimpression","restock","inventory cycle"),
 "retail":("retail","distribution","détaillant"),
 "commerce":("commerce","marketplace","transaction costs"),
 "resale":("resale","revente","secondhand"),
 "market_microstructure":("bid-ask","market microstructure","microstructure"),
}
def intake_public_study(*,source_url,published_at,observed_at,title,text):
    if not isinstance(source_url,str) or not source_url.startswith("https://") or len(source_url)>2000:raise ValueError("invalid source")
    if _time(published_at)>_time(observed_at):raise ValueError("future publication")
    if not isinstance(title,str) or not 5<=len(title)<=300:raise ValueError("invalid title")
    if not isinstance(text,str) or not 50<=len(text)<=MAX_TEXT:raise ValueError("invalid or oversized text")
    normalized=re.sub(r"\s+"," ",text).strip()
    matches={topic for topic,keywords in TOPIC_TERMS.items() if any(kw.casefold() in normalized.casefold() for kw in keywords)}
    digest=hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return {"schema":"edge.learning.acquisition.v1","source_url":source_url,
        "published_at":published_at,"observed_at":observed_at,"title":title,
        "text_sha256":digest,"text_characters":len(normalized),
        "candidate_topics":sorted(matches),"status":"UNREVIEWED_SOURCE",
        "lesson_generated":False,"knowledge_adopted":False,
        "policy_change_authorized":False}

def compare_candidate_on_holdout(lesson, baseline, challenger):
    """The caller must supply pre-labeled, held-out booleans; no invented ground truth."""
    from intelligence.learning_intelligence import evaluate_lesson
    result=evaluate_lesson(lesson,baseline_cases=baseline,challenger_cases=challenger)
    result["evaluation_data_origin"]="CALLER_SUPPLIED_UNVERIFIED"
    result["prospective_validation_established"]=False
    return result
