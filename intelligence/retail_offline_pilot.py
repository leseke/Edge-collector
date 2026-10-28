"""Deterministic offline pilot for retail signals, not evidence of market edge.

Synthetic timelines only. Strict past-only snapshots prevent lookahead.
"""
from intelligence.prediction_journal import _dt
from intelligence.retail_radar import normalize_offer
from intelligence.retail_signal_confirmation import confirm_retail_signals

CASES=(
 ("POKEMON","TCG","pokemon-sealed-fr","shop.cafemeisia.com","meisia",
  (("09:00","OUT_OF_STOCK","139"),("10:00","IN_STOCK","139"),("11:00","IN_STOCK","139"))),
 ("LEGO","LEGO","lego-10365","example.org","fixture-lego",
  (("09:00","IN_STOCK","199"),("10:00","IN_STOCK","179"),("11:00","IN_STOCK","199"))),
)
def run_offline_retail_pilot(*,as_of="2026-10-28T12:00:00Z"):
    cutoff=_dt(as_of)
    records=[]
    for _,vertical,product,domain,source,history in CASES:
        for hour,state,price in history:
            row=normalize_offer(source_id=source,source_domain=domain,
                listing_url="https://"+domain+"/fixture",actual_seller=source,
                product_key=product,vertical=vertical,offer_state=state,
                price_eur=price,observed_at="2026-10-28T"+hour+":00Z")
            if _dt(row["observed_at"])<=cutoff:records.append(row)
    signals=confirm_retail_signals(records)
    return {"schema":"edge.retail.offline_pilot.v1","synthetic_fixture_only":True,
        "observations":len(records),"signal_candidates":len(signals),
        "source_reconfirmed":sum(s["status"]=="SOURCE_RECONFIRMED" for s in signals),
        "unconfirmed":sum(s["status"]=="UNCONFIRMED" for s in signals),
        "signal_details":signals,
        "market_data_collected":False,"economic_edge_proven":False,
        "false_positive_rate":None,"purchase_authorized":False}
