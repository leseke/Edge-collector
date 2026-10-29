"""Validate a locally provided TCGdex FR catalogue response.

Catalogue identities only: no availability, sold prices or financial ranking.
No network access and no API credentials.
"""
import json
from hashlib import sha256
from intelligence.prediction_journal import _dt

def inspect_tcgdex_sets(raw, *, observed_at):
    _dt(observed_at)
    if not isinstance(raw,bytes) or not 2<=len(raw)<=1_000_000:
        raise ValueError("bounded JSON response required")
    data=json.loads(raw)
    if not isinstance(data,list) or len(data)>2000:
        raise ValueError("sets must be a bounded list")
    if not data:\n        raise ValueError("empty catalogue cannot establish coverage")\n    ids=set()
    records=[]
    for item in data:
        if not isinstance(item,dict):
            raise ValueError("invalid set")
        sid=item.get("id")
        name=item.get("name")
        if not isinstance(sid,str) or not 1<=len(sid)<=80 or not isinstance(name,str) or not 1<=len(name)<=200:
            raise ValueError("invalid set identity")
        if sid.strip()!=sid or name.strip()!=name or not sid.strip() or not name.strip():\n            raise ValueError("blank catalogue identity")\n        if sid in ids:
            raise ValueError("duplicate set ID")
        ids.add(sid)
        records.append({"set_id":sid,"set_name":name})
    return {"schema":"edge.tcg.catalogue_review.v1",
        "source":"TCGdex FR API","observed_at":observed_at,
        "source_snapshot_sha256":sha256(raw).hexdigest(),
        "sets":records,"set_count":len(records),"coverage":"SNAPSHOT_ONLY",
        "live_api_authenticated":False,
        "sealed_product_catalogue":False,
        "market_offer_evidence":False,
        "completed_sale_verified":False,
        "purchase_authorized":False}
