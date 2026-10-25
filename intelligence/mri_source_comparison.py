"""MRI-007: conservative cross-source evidence comparison.

Lexical matches are NOT independent confirmation. A source may be a syndicated
copy; event targets and real-world facts remain unverified.
"""
import hashlib
import re
from urllib.parse import urlsplit
from intelligence.actor_intelligence import _time

NEG=re.compile(r"\b(?:no|not|never|false|denied|cancelled|canceled|aucun|pas de|démenti|annulé|sans)\b",re.I)

def compare_sources(digests, as_of):
    cutoff=_time(as_of)
    if not isinstance(digests,list):raise ValueError("digests list required")
    rows=[];seen=set()
    for doc in digests:
        if not isinstance(doc,dict) or doc.get("schema")!="edge.mri.event_candidates.v1" or doc.get("coverage")!="COMPLETE" or doc.get("policy_decision")!="NOT_EVALUATED":
            raise ValueError("invalid evidence digest")
        for c in doc.get("candidates",[]):
            if c.get("verification_status")!="CANDIDATE_UNVERIFIED" or c.get("occurred_at") is not None:
                raise ValueError("candidate is not unverified")
            if _time(c["observed_at"])>cutoff:continue
            uri=urlsplit(c["source_url"])
            if uri.scheme!="https" or not uri.hostname:raise ValueError("invalid source URL")
            key=(doc["source_id"],c["event_id"])
            if key in seen:raise ValueError("duplicate event candidate")
            seen.add(key)
            quote=re.sub(r"\s+"," ",c["quote"]).strip()
            rows.append({"source_id":doc["source_id"],"event_id":c["event_id"],
                         "source_host":uri.hostname.lower(),"action_type":c["action_type"],
                         "source_url":c["source_url"],"observed_at":c["observed_at"],
                         "quote":quote,"text_hash":hashlib.sha256(quote.lower().encode()).hexdigest(),
                         "polarity":"NEGATION_CUE" if NEG.search(quote) else "NO_NEGATION_CUE"})
    groups=[]
    for action in sorted({r["action_type"] for r in rows}):
        matches=[r for r in rows if r["action_type"]==action]
        hosts={r["source_host"] for r in matches}
        hashes={r["text_hash"] for r in matches}
        groups.append({"action_type":action,"source_count":len(matches),
                       "distinct_hosts":len(hosts),"distinct_texts":len(hashes),
                       "negation_cue_present":any(r["polarity"]=="NEGATION_CUE" for r in matches),
                       "status":"MULTISOURCE_MENTION_UNVERIFIED" if len(hosts)>1 else "SINGLE_HOST_MENTION_UNVERIFIED",
                       "same_event_confirmed":False,
                       "independent_sources_confirmed":False,
                       "candidates":sorted(matches,key=lambda x:(x["observed_at"],x["event_id"]))})
    return {"schema":"edge.mri.source_comparison.v1","as_of":as_of,
            "status":"RESEARCH_ONLY","review_required":True,
            "policy_decision":"NOT_EVALUATED","groups":groups}
