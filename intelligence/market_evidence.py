"""EDGE Market Evidence Layer V1.

Observed sold transactions, live asks, and estimates are NEVER interchangeable.
Every entry is bound to exact product identity and traceable provenance.
No network, payment, forecast, or trade authorization.
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from statistics import median
from intelligence.opportunity_identity import product_identity

KINDS={"SOLD","ASK","ESTIMATE"}
REQUIRED={"observation_id","product","kind","price_eur","quantity","observed_at","source_url","source_record_id"}

def _timestamp(value):
    if not isinstance(value,str):raise ValueError("timestamp string required")
    dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    if dt.tzinfo is None:raise ValueError("timezone required")
    return dt.astimezone(timezone.utc)

def validate_evidence(row):
    if not isinstance(row,dict) or set(row)!=REQUIRED:raise ValueError("strict evidence schema required")
    ident=product_identity(row["product"])
    if not ident["identity_complete"]:raise ValueError("unresolved product identity")
    if row["kind"] not in KINDS:raise ValueError("invalid kind")
    if type(row["quantity"]) is not int or row["quantity"]<1 or row["quantity"]>100000:raise ValueError("invalid quantity")
    try:
        if isinstance(row["price_eur"],bool):raise ValueError("invalid price")
        price=Decimal(str(row["price_eur"]))
    except (InvalidOperation,TypeError):raise ValueError("invalid price")
    if not price.is_finite() or price<0:raise ValueError("invalid price")
    if any(not isinstance(row[k],str) or not row[k].strip() or len(row[k])>2000 for k in ("observation_id","source_url","source_record_id")):
        raise ValueError("invalid provenance")
    if not row["source_url"].startswith("https://"):raise ValueError("https source required")
    _timestamp(row["observed_at"])
    return ident,price

def market_snapshot(evidence, as_of):
    cutoff=_timestamp(as_of)
    if not isinstance(evidence,list):raise ValueError("evidence list required")
    rows=[];ids=set();seen_records=set();product_key=None
    for row in evidence:
        ident,price=validate_evidence(row)
        if product_key is None:product_key=ident["key"]
        if ident["key"]!=product_key:raise ValueError("mixed product identities")
        if row["observation_id"] in ids:raise ValueError("duplicate observation id")
        ids.add(row["observation_id"])
        record=(row["kind"],row["source_url"],row["source_record_id"])
        if record in seen_records:raise ValueError("duplicate marketplace record")
        seen_records.add(record)
        if _timestamp(row["observed_at"])<=cutoff:rows.append((row,price))
    sold=[(r,p) for r,p in rows if r["kind"]=="SOLD"]
    asks=[(r,p) for r,p in rows if r["kind"]=="ASK"]
    estimates=[(r,p) for r,p in rows if r["kind"]=="ESTIMATE"]
    def med(group):
        return str(median([p for _,p in group])) if group else None
    sold_qty=sum(r["quantity"] for r,_ in sold)
    return {"schema":"edge.market.evidence.v1","as_of":as_of,"product_key":product_key,
            "sold_records":len(sold),"sold_units_observed":sold_qty,
            "sold_median_eur":med(sold),"asking_records":len(asks),
            "asking_median_eur":med(asks),"estimate_records":len(estimates),
            "estimate_median_eur":med(estimates),
            "liquidity_status":"NOT_ESTIMABLE",
            "volume_is_market_total":False,
            "sold_records_verified_independent":False,
            "decision":"NOT_EVALUATED","execution_authorized":False}
