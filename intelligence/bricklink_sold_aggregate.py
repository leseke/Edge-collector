"""BrickLink official sold price-guide adapter (offline payload).

Consumes an authorized response from GET /items/SET/{no}/price?guide_type=sold.
No credentials, network access, scraping, execution, or market BUY decisions.
Sold aggregates are not independently authenticated transactions.
"""
import hashlib
import json
from decimal import Decimal, InvalidOperation
from intelligence.prediction_journal import _dt

def _price(value):
    try:
        if isinstance(value,bool):raise ValueError("invalid monetary value")
        d=Decimal(str(value))
    except (InvalidOperation,TypeError,ValueError):
        raise ValueError("invalid monetary value")
    if not d.is_finite() or d<0 or d>Decimal("1000000000"):
        raise ValueError("invalid monetary value")
    return d

def parse_bricklink_sold_priceguide(payload,*,set_no,condition,currency,observed_at):
    _dt(observed_at)
    if not isinstance(payload,dict) or not isinstance(payload.get("data"),dict):
        raise ValueError("BrickLink API data missing")
    if not isinstance(set_no,str) or not set_no or len(set_no)>80 or condition not in ("N","U"):
        raise ValueError("invalid exact set/condition")
    if currency not in ("EUR","USD","GBP"):
        raise ValueError("unsupported currency")
    data=payload["data"]
    item=data.get("item")
    if not isinstance(item,dict) or item.get("type")!="SET" or item.get("no")!=set_no:
        raise ValueError("item identity mismatch")
    if data.get("new_or_used")!=condition or data.get("currency_code")!=currency:
        raise ValueError("variant or currency mismatch")
    units=data.get("total_quantity");events=data.get("unit_quantity")
    if any(type(x) is not int or x<0 for x in (units,events)):
        raise ValueError("invalid sale counts")
    avg=_price(data.get("avg_price"));weighted=_price(data.get("qty_avg_price"))
    low=_price(data.get("min_price"));high=_price(data.get("max_price"))
    if units and (not events or low>high or not low<=avg<=high or not low<=weighted<=high):
        raise ValueError("inconsistent price guide")
    if not units and (events or any(x!=0 for x in (avg,weighted,low,high))):
        raise ValueError("nonzero stats with zero units")
    canonical=json.dumps(payload,sort_keys=True,ensure_ascii=False,separators=(",",":"))
    return {"schema":"edge.market.bricklink_sold_aggregate.v1",
            "provider":"BRICKLINK_OFFICIAL_API_RESPONSE_CLAIM",
            "guide_type":"sold","window":"ROLLING_LAST_6_MONTHS",
            "set_no":set_no,"condition":condition,"currency":currency,
            "observed_at":observed_at,"events":events,"units":units,
            "average_price":str(avg),"quantity_weighted_average":str(weighted),
            "min_price":str(low),"max_price":str(high),
            "source_payload_sha256":hashlib.sha256(canonical.encode()).hexdigest(),
            "vat_and_shipping_included":False,
            "individual_transactions_verified":False,
            "external_payload_authenticity_verified":False,
            "outcome_learning_eligible":False,
            "purchase_authorized":False}
