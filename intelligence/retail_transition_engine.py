"""Conservative market radar: confirm transitions only from repeated observations.

A source-reported stock change is a signal, NOT proof of a physical restock.
No sales inference, no extrapolation across product variants or sellers.
"""
from decimal import Decimal
from intelligence.prediction_journal import _dt

def detect_retail_transitions(observations):
    if not isinstance(observations,list) or len(observations)>5000:
        raise ValueError("bounded observations required")
    by_key={}
    for row in observations:
        if not isinstance(row,dict) or row.get("schema")!="edge.retail.observation.v1":
            raise ValueError("normalized retail observation required")
        stamp=_dt(row["observed_at"])
        if any(row.get(k) is not False for k in ("completed_sale_evidence","event_confirmed","purchase_authorized")):
            raise ValueError("untrusted observation promoted")
        key=(row["source_id"],row["seller"],row["product_key"],row["vertical"])
        by_key.setdefault(key,[]).append(row)
    events=[]
    for key,series in by_key.items():
        series.sort(key=lambda r:_dt(r["observed_at"]))
        for prev,new in zip(series,series[1:]):
            if _dt(new["observed_at"])<=_dt(prev["observed_at"]):
                raise ValueError("duplicate or reversed timestamp")
            kind=None
            if prev["offer_state"]=="OUT_OF_STOCK" and new["offer_state"]=="IN_STOCK":
                kind="RESTOCK_CANDIDATE"
            elif prev["price_eur"] is not None and new["price_eur"] is not None:
                if Decimal(prev["price_eur"])!=Decimal(new["price_eur"]):
                    kind="PRICE_CHANGE_CANDIDATE"
            if kind:
                events.append({"schema":"edge.retail.transition.v1","event":kind,
                    "source_id":key[0],"seller":key[1],"product_key":key[2],
                    "vertical":key[3],"previous_at":prev["observed_at"],
                    "observed_at":new["observed_at"],"previous_state":prev["offer_state"],
                    "new_state":new["offer_state"],"previous_price_eur":prev["price_eur"],
                    "new_price_eur":new["price_eur"],"source_reported_only":True,
                    "physical_restock_proven":False,"market_sales_proven":False,
                    "investment_recommendation":False,"purchase_authorized":False})
    return sorted(events,key=lambda e:(e["observed_at"],e["source_id"],e["product_key"]))
