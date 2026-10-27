"""One-shot read-only BrickLink research observation job.

Credentials supplied only at runtime; injected transport supports offline tests.
No orders, deployments, or publication. Source authenticity is not inferred.
"""
from intelligence.bricklink_oauth_client import fetch_sold_aggregate
from intelligence.bricklink_observation_journal import append_observation

def collect_and_record(*,journal_path,set_no,condition,currency,observed_at,credentials,transport=None):
    observation=fetch_sold_aggregate(set_no=set_no,condition=condition,currency=currency,
        observed_at=observed_at,credentials=credentials,transport=transport)
    entry=append_observation(journal_path,observation)
    return {"schema":"edge.market.bricklink_collection.v1",
        "status":"OBSERVED_UNVERIFIED_AGGREGATE","observation_id":entry["id"],
        "product_reference":set_no,"condition":condition,"currency":currency,
        "units_last_six_months":observation["units"],
        "rolling_window_not_daily_sales":True,
        "price_data_authenticated_as_live":False,
        "automated_orders":False,"learning_verified_outcomes":0}
