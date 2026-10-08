import os, requests
from datetime import datetime, timedelta

APIFY = os.environ["APIFY_TOKEN"]
ACTOR = "caffein.dev~ebay-sold-listings"


def fetch_sold(query, days=90, count=100, condition="new"):
    """Recupere les ventes eBay confirmees via Apify.
    condition='new' filtre les produits neufs uniquement.
    Dédoublonne par itemId pour eviter les faux comptes.
    """
    url = (f"https://api.apify.com/v2/acts/{ACTOR}"
           f"/run-sync-get-dataset-items?token={APIFY}")
    payload = {
        "keyword": query,
        "maxItems": count,
    }
    r = requests.post(url, json=payload, timeout=300)
    r.raise_for_status()
    items = r.json()

    if not items:
        return None

    # Filtre 1 : etat du produit (si 'new')
    if condition == "new":
        items = [it for it in items
                 if (it.get("condition") or "").lower() in
                 ("brand new", "new", "neu", "neuf")]
        if not items:
            return None

    # Filtre 2 : dedoublonnage par itemId
    seen = set()
    unique = []
    for it in items:
        iid = it.get("itemId")
        if iid and iid in seen:
            continue
        if iid:
            seen.add(iid)
        unique.append(it)
    items = unique

    # Extraction des prix
    prices = []
    for it in items:
        p = it.get("soldPrice")
        if p is None:
            continue
        try:
            prices.append(float(p))
        except (ValueError, TypeError):
            continue

    if not prices:
        return None

    prices_sorted = sorted(prices)
    median = prices_sorted[len(prices_sorted) // 2]

    # Comptage des ventes sur 30 jours glissants
    now = datetime.utcnow()
    cutoff_30 = now - timedelta(days=30)
    recent_30 = 0
    for it in items:
        end = it.get("endedAt")
        if not end:
            continue
        try:
            dt = datetime.fromisoformat(end.replace("Z", ""))
            if dt >= cutoff_30:
                recent_30 += 1
        except Exception:
            pass

    return {
        "product_id": query.lower().replace(" ", "_"),
        "source": "ebay_sold_us",
        "captured_at": now.isoformat(),
        "sold_price_avg": round(sum(prices) / len(prices), 2),
        "sold_price_median": round(median, 2),
        "sold_count_30d": recent_30,
        "active_listings": None,
        "sell_through": None,
        "lowest_ask": round(min(prices), 2),
        "currency": items[0].get("soldCurrency", "USD"),
        "raw_json": None,
    }