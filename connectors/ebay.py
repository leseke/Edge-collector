import os, re, requests
from datetime import datetime, timedelta

APIFY = os.environ["APIFY_TOKEN"]
ACTOR = "caffein.dev~ebay-sold-listings"


def fetch_sold(query, must_all=None, must_any=None, count=100,
               days_window=90):
    """Recherche eBay + filtre strict sur le titre.

    must_all : liste de mots qui DOIVENT tous etre dans le titre
    must_any : liste de mots dont AU MOINS UN doit etre dans le titre
    """
    must_all = [m.lower() for m in (must_all or [])]
    must_any = [m.lower() for m in (must_any or [])]

    url = (f"https://api.apify.com/v2/acts/{ACTOR}"
           f"/run-sync-get-dataset-items?token={APIFY}")
    payload = {"keyword": query, "maxItems": count}

    r = requests.post(url, json=payload, timeout=300)
    r.raise_for_status()
    items = r.json()
    if not items:
        return None

    def title_ok(it):
        t = (it.get("title") or "").lower()
        if not t:
            return False
        for w in must_all:
            if w not in t:
                return False
        if must_any:
            if not any(w in t for w in must_any):
                return False
        return True

    # Filtres successifs
    items = [it for it in items if title_ok(it)]
    items = [it for it in items
             if (it.get("condition") or "").lower() in
             ("brand new", "new", "neu", "neuf")]
    if not items:
        return None

    # Dedoublonnage
    seen, unique = set(), []
    for it in items:
        iid = it.get("itemId")
        if iid and iid in seen:
            continue
        if iid:
            seen.add(iid)
        unique.append(it)
    items = unique

    # Prix
    prices = []
    for it in items:
        try:
            prices.append(float(it["soldPrice"]))
        except (KeyError, ValueError, TypeError):
            continue
    if not prices:
        return None

    prices_sorted = sorted(prices)
    n = len(prices_sorted)
    median = prices_sorted[n // 2]

    # Moyenne tronquee : on enleve les 10% extremes
    k = max(1, n // 10)
    trimmed = prices_sorted[k:n-k] if n > 2*k else prices_sorted
    trimmed_avg = sum(trimmed) / len(trimmed)

    # Ecart-type pour detecter les requetes polluees
    mean = sum(prices) / n
    var = sum((p - mean) ** 2 for p in prices) / n
    std = var ** 0.5
    cv = std / mean if mean > 0 else 0  # coefficient de variation

    # Comptage 30 jours glissants
    now = datetime.utcnow()
    cutoff = now - timedelta(days=30)
    recent = 0
    for it in items:
        end = it.get("endedAt")
        if not end:
            continue
        try:
            dt = datetime.fromisoformat(end.replace("Z", ""))
            if dt >= cutoff:
                recent += 1
        except Exception:
            pass

    return {
        "product_id": query.lower().replace(" ", "_"),
        "source": "ebay_sold_us",
        "captured_at": now.isoformat(),
        "sold_price_avg": round(trimmed_avg, 2),
        "sold_price_median": round(median, 2),
        "sold_count_30d": recent,
        "active_listings": None,
        "sell_through": None,
        "lowest_ask": round(min(prices), 2),
        "currency": items[0].get("soldCurrency", "USD"),
        "raw_json": None,
        "_n_filtered": n,
        "_cv": round(cv, 2),
        "_filtered_out": count - n,
    }