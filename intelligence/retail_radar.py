"""Generic EDGE retail radar: shared retail observation semantics across markets.

Market-specific scarcity and resale models remain separate. No inferred sales.
"""
from decimal import Decimal,InvalidOperation
from urllib.parse import urlsplit
from intelligence.prediction_journal import _dt

VERTICALS={"TCG","LEGO","SNEAKERS","WATCHES","LIMITED_APPAREL","COLLECTIBLES","OTHER"}
STATES={"IN_STOCK","OUT_OF_STOCK","PREORDER","UNKNOWN"}
EVENTS={"OBSERVATION","RESTOCK_CANDIDATE","PRICE_CHANGE_CANDIDATE","PREORDER_CANDIDATE"}
def normalize_offer(*,source_id,source_domain,listing_url,actual_seller,product_key,
                    vertical,offer_state,observed_at,price_eur=None,event="OBSERVATION"):
    _dt(observed_at)
    if vertical not in VERTICALS or offer_state not in STATES or event not in EVENTS:
        raise ValueError("unsupported classification")
    for field in (source_id,actual_seller,product_key):
        if not isinstance(field,str) or not field.strip() or len(field)>200:
            raise ValueError("identity required")
    if not isinstance(source_domain,str) or not source_domain or "/" in source_domain:
        raise ValueError("invalid registered domain")
    u=urlsplit(listing_url)
    host=(u.hostname or "").lower()
    if u.scheme!="https" or (host!=source_domain and not host.endswith("."+source_domain)) or u.username or u.password or u.fragment:
        raise ValueError("source URL mismatch")
    amount=None
    if price_eur is not None:
        try: v=Decimal(str(price_eur))
        except (InvalidOperation,TypeError,ValueError):raise ValueError("invalid price")
        if not v.is_finite() or not 0<v<Decimal("1000000000"):raise ValueError("invalid price")
        amount=str(v)
    return {"schema":"edge.retail.observation.v1","source_id":source_id,
            "source_url":listing_url,"seller":actual_seller.strip(),"product_key":product_key,
            "vertical":vertical,"offer_state":offer_state,"event_candidate":event,
            "price_eur":amount,"observed_at":observed_at,
            "event_confirmed":False,"seller_authenticated":False,
            "stock_independently_verified":False,"completed_sale_evidence":False,
            "scarcity_inferred":False,"investment_recommendation":False,
            "purchase_authorized":False}
