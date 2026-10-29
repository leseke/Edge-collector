"""MRI-006: evidence-linked event candidates, not autonomous factual assertions.

All chunks are scanned; matches are leads requiring human/source verification.
No inferred historical event dates, no BUY signals, no unverified causality.
"""
import re
from hashlib import sha256

PATTERNS = {
    "launch": re.compile(r"\b(?:launch(?:ed|ing)?|release(?:d)?|sortie|lancement|lanc[ée])\b",re.I),
    "reprint": re.compile(r"\b(?:reprint|reimpression|réimpression|réédition|restock)\b",re.I),
    "delisting": re.compile(r"\b(?:retiré|retrait|retirement|retired|discontinued)\b",re.I),
    "price_change": re.compile(r"\b(?:prix|price|tarif|pricing)\b",re.I),
}
def extract_candidates(evidence, observed_at):
    if not isinstance(evidence,dict) or evidence.get("schema")!="edge.mri.evidence_segments.v1" or evidence.get("complete") is not True:
        raise ValueError("complete evidence required")
    segments=evidence["segments"]
    text="".join(p["text"] for p in segments)
    if len(text)!=evidence["total_characters"] or sha256(text.encode("utf-8")).hexdigest()!=evidence["source_sha256"]:
        raise ValueError("source integrity failed")
    from intelligence.actor_intelligence import _time
    _time(observed_at)
    findings=[]
    for typ,pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            pos=match.start()
            start=max(0,pos-90);end=min(len(text),match.end()+100)
            indexes=[p["index"] for p in segments if p["start"]<end and p["end"]>start]
            findings.append({"event_id":sha256((evidence["source_sha256"]+typ+str(pos)).encode()).hexdigest()[:20],
                "action_type":typ,"source_url":evidence["source_url"],
                "source_sha256":evidence["source_sha256"],"start":start,"end":end,
                "segment_indexes":indexes,"quote":text[start:end],
                "observed_at":observed_at,"occurred_at":None,
                "verification_status":"CANDIDATE_UNVERIFIED"})
    findings.sort(key=lambda r:(r["start"],r["action_type"]))
    return {"schema":"edge.mri.event_candidates.v1","review_required":True,"policy_decision":"NOT_EVALUATED",
            "source_id":evidence["source_id"],"scanned_characters":len(text),
            "coverage":"COMPLETE","candidates":findings}
