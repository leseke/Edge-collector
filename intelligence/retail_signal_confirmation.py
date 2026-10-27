"""Retail signal confirmation layer: conservative repeated-observation evidence.

It does not infer physical restocks, sales or investment return. Confirmation
means that a source-reported state persisted across timestamped observations.
"""
from intelligence.prediction_journal import _dt
from intelligence.retail_transition_engine import detect_retail_transitions

def confirm_retail_signals(observations, *, minimum_confirmations=2):
    if type(minimum_confirmations) is not int or minimum_confirmations<2 or minimum_confirmations>10:
        raise ValueError("minimum confirmations must be 2..10")
    events=detect_retail_transitions(observations)
    groups={}
    for row in observations:
        k=(row["source_id"],row["seller"],row["product_key"],row["vertical"])
        groups.setdefault(k,[]).append(row)
    results=[]
    for event in events:
        k=(event["source_id"],event["seller"],event["product_key"],event["vertical"])
        later=sorted((x for x in groups[k] if _dt(x["observed_at"])>=_dt(event["observed_at"])),key=lambda x:_dt(x["observed_at"]))
        confirmed=0
        for row in later:
            same=(row["offer_state"]==event["new_state"] if event["event"]=="RESTOCK_CANDIDATE" else row["price_eur"]==event["new_price_eur"])
            if not same:break
            confirmed+=1
        passed=confirmed>=minimum_confirmations
        results.append({"schema":"edge.retail.signal_confirmation.v1",
            "source_id":event["source_id"],"seller":event["seller"],"product_key":event["product_key"],
            "vertical":event["vertical"],"event":event["event"],"first_detected_at":event["observed_at"],
            "consecutive_observations":confirmed,
            "status":"SOURCE_RECONFIRMED" if passed else "UNCONFIRMED",
            "physical_stock_verified":False,"completed_sales_verified":False,
            "buy_recommendation":False,"purchase_authorized":False})
    return results
