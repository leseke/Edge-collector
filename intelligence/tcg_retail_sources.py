"""TCG retail source registry: discovery inputs, never proof of completed sales.

Storefront domain does not establish the seller of a marketplace offer.
No scraping, buying, pricing claim or automated provider authentication.
"""
from urllib.parse import urlsplit
from intelligence.retail_radar import normalize_offer

SOURCES={
 "ludisphere":{"domain":"ludisphere.fr","category":"SPECIALIST","verticals":["POKEMON","TCG"],"seller_mode":"DIRECT_TO_VERIFY"},
 "meisia":{"domain":"shop.cafemeisia.com","category":"SPECIALIST","verticals":["POKEMON","TCG"],"seller_mode":"DIRECT_TO_VERIFY"},
 "mystic_games":{"domain":"mysticgames.fr","category":"SPECIALIST","verticals":["POKEMON","TCG"],"seller_mode":"DIRECT_TO_VERIFY"},
 "1piecetcg":{"domain":"1piecetcg.fr","category":"SPECIALIST","verticals":["ONE_PIECE"],"seller_mode":"DIRECT_TO_VERIFY"},
 "fnac":{"domain":"fnac.com","category":"GENERAL_RETAIL","verticals":["POKEMON","TCG"],"seller_mode":"DIRECT_OR_MARKETPLACE"},
 "cultura":{"domain":"cultura.com","category":"GENERAL_RETAIL","verticals":["POKEMON","TCG"],"seller_mode":"DIRECT_OR_MARKETPLACE"},
 "leclerc":{"domain":"e.leclerc","category":"GENERAL_RETAIL","verticals":["POKEMON","TCG"],"seller_mode":"DIRECT_OR_MARKETPLACE"},
 "auchan":{"domain":"auchan.fr","category":"GENERAL_RETAIL","verticals":["POKEMON","TCG"],"seller_mode":"DIRECT_OR_MARKETPLACE"},
}

def classify_retail_offer(*,source_id,listing_url,actual_seller,product_key,offer_state,observed_at):
    from intelligence.prediction_journal import _dt
    _dt(observed_at)
    if source_id not in SOURCES:raise ValueError("unregistered source")
    source=SOURCES[source_id]
    u=urlsplit(listing_url)
    host=(u.hostname or "").lower()
    domain=source["domain"]
    if u.scheme!="https" or host!=domain and not host.endswith("."+domain) or u.username or u.password or u.fragment:
        raise ValueError("source URL does not match registry")
    if not isinstance(actual_seller,str) or not actual_seller.strip() or len(actual_seller)>180:
        raise ValueError("actual seller required")
    if not isinstance(product_key,str) or not product_key.strip():
        raise ValueError("exact product key required")
    if offer_state not in ("IN_STOCK","OUT_OF_STOCK","PREORDER","UNKNOWN"):
        raise ValueError("invalid offer state")
    common=normalize_offer(source_id=source_id,source_domain=domain,listing_url=listing_url,
       actual_seller=actual_seller,product_key=product_key,vertical="TCG",
       offer_state=offer_state,observed_at=observed_at)
    return {"schema":"edge.tcg.retail_offer.v1","source_id":source_id,
        "source_category":source["category"],"source_url":listing_url,
        "actual_seller":actual_seller.strip(),"product_key":product_key,
        "offer_state":offer_state,"observed_at":observed_at,
        "seller_verified":False,"stock_independently_verified":False,
        "sale_count_inferred":False,"completed_sale_evidence":False,
        "retail_research_only":True,"purchase_authorized":False,
            "common_radar":common}
