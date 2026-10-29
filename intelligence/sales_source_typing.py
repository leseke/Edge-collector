"""Strict source typing before any sales evidence enters prospective evaluation.

Never infer an actual sale from asking prices, sold badges or seller claims.
"""
from decimal import Decimal,InvalidOperation
from urllib.parse import urlsplit
from intelligence.prediction_journal import _dt

TYPES={"ASK","SELLER_CLAIM","MARKETPLACE_SOLD_RECORD","SETTLEMENT_RECEIPT"}
def classify_sales_observations(records,*,as_of):
    cutoff=_dt(as_of)
    if not isinstance(records,list) or len(records)>500:raise ValueError("bounded evidence list required")
    seen=set();counts={k:0 for k in sorted(TYPES)};rejected=[]
    for index,r in enumerate(records):
        if not isinstance(r,dict) or set(r)!={"evidence_id","record_type","product_key","source_url","observed_at","amount_eur","proof_sha256"}:
            raise ValueError("strict typed record required")
        ident=r["evidence_id"]
        if not isinstance(ident,str) or not ident or ident in seen:raise ValueError("duplicate evidence id")
        seen.add(ident)
        kind=r["record_type"]
        if kind not in TYPES:raise ValueError("unknown evidence type")
        url=urlsplit(r["source_url"])
        if url.scheme!="https" or not url.hostname or url.username or url.password:raise ValueError("invalid source url")
        if _dt(r["observed_at"])>cutoff:raise ValueError("future evidence")
        try: amount=Decimal(str(r["amount_eur"]))
        except (ValueError,InvalidOperation):raise ValueError("invalid amount")
        if not amount.is_finite() or not 0<amount<Decimal("1000000000"):raise ValueError("invalid amount")
        proof=r["proof_sha256"]
        if not isinstance(proof,str) or len(proof)!=64 or any(ch not in "0123456789abcdef" for ch in proof):
            raise ValueError("source snapshot SHA-256 required")
        if not isinstance(r["product_key"],str) or not r["product_key"]:raise ValueError("product identity required")
        counts[kind]+=1
        if kind!="SETTLEMENT_RECEIPT":
            rejected.append({"evidence_id":ident,"reason":"NOT_SETTLEMENT_PROOF"})
        else:
            rejected.append({"evidence_id":ident,"reason":"SETTLEMENT_NOT_INDEPENDENTLY_AUTHENTICATED"})
    return {"schema":"edge.learning.sales_source_audit.v1","counts":counts,"records_checked":len(seen),
        "verified_transactions":0,"rejected_for_learning":rejected,
        "learning_eligible":False,"purchase_authorized":False}
