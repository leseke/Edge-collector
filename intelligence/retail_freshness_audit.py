"""Private observation freshness and coverage audit, not a trading signal.

Uses journal snapshots only, with strict as-of cutoff. A missing source does
not imply stock depletion; stale observations are not current offers.
"""
from collections import defaultdict
from intelligence.prediction_journal import _dt
from intelligence.retail_observation_history import _read

def audit_retail_freshness(path, *, as_of, stale_after_hours=24):
    now=_dt(as_of)
    if type(stale_after_hours) is not int or not 1<=stale_after_hours<=720:
        raise ValueError("stale_after_hours must be 1..720")
    groups=defaultdict(list)
    excluded_future=0
    for record in _read(path):
        row=record["observation"]
        at=_dt(row["observed_at"])
        if at>now:
            excluded_future+=1
            continue
        key=(row["source_id"],row["seller"],row["product_key"],row["vertical"])
        groups[key].append(row)
    out=[]
    for key, observations in sorted(groups.items()):
        last=max(observations,key=lambda item:_dt(item["observed_at"]))
        age=(now-_dt(last["observed_at"])).total_seconds()/3600
        stale=age>stale_after_hours
        out.append({"source_id":key[0],"seller":key[1],"product_key":key[2],
                    "vertical":key[3],"last_observed_at":last["observed_at"],
                    "age_hours":round(age,3),"observations":len(observations),
                    "freshness":"STALE" if stale else "RECENT_SOURCE_CLAIM",
                    "offer_state":last["offer_state"] if not stale else "UNKNOWN_STALE",
                    "source_authenticated":False,"stock_verified":False,
                    "sale_verified":False,"purchase_authorized":False})
    return {"schema":"edge.retail.freshness_audit.v1","as_of":as_of,
            "stale_after_hours":stale_after_hours,"tracked_offers":len(out),
            "stale_offers":sum(x["freshness"]=="STALE" for x in out),
            "future_records_excluded":excluded_future,"offers":out,
            "real_world_accuracy_unverified":True,"purchase_authorized":False}
