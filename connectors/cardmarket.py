import os, json, requests
from datetime import datetime

APIFY = os.environ["APIFY_TOKEN"]
ACTOR = "unfenced-group~cardmarket-scraper"


def fetch_cardmarket(game, search_query, product_type="sealed",
                     must_all=None, must_any=None, must_not=None):
    """Recupere les donnees Cardmarket via Apify.
    Retourne un snapshot unifie (EUR) ou None.
    """
    must_all = [m.lower() for m in (must_all or [])]
    must_any = [m.lower() for m in (must_any or [])]
    must_not = [m.lower() for m in (must_not or [])]

    url = (f"https://api.apify.com/v2/acts/{ACTOR}"
           f"/run-sync-get-dataset-items?token={APIFY}")
    payload = {
        "game": game,
        "searchQuery": search_query,
        "productType": product_type,
    }
    r = requests.post(url, json=payload, timeout=300)
    r.raise_for_status()
    items = r.json()
    if not items:
        return None

    def title_ok(it):
        t = (it.get("name") or "").lower()
        if not t:
            return False
        for w in must_all:
            if w not in t:
                return False
        if must_any and not any(w in t for w in must_any):
            return False
        for w in must_not:
            if w in t:
                return False
        return True

    items = [it for it in items if title_ok(it)]
    priced = [it for it in items if it.get("trendEur") is not None]
    if not priced:
        return None

    trends = sorted(float(it["trendEur"]) for it in priced)
    lows = [float(it["lowEur"]) for it in priced if it.get("lowEur")]

    n = len(trends)
    median = trends[n // 2]
    k = max(1, n // 10)
    trimmed = trends[k:n-k] if n > 2*k else trends
    trimmed_avg = sum(trimmed) / len(trimmed)

    best = priced[0]
    now = datetime.utcnow()

    raw = {
        "expansion": best.get("expansionName"),
        "trendVsLowPct": best.get("trendVsLowPct"),
        "momentum7Pct": best.get("momentum7Pct"),
        "momentum30Pct": best.get("momentum30Pct"),
        "euUsSpreadPct": best.get("euUsSpreadPct"),
        "n_matched": len(priced),
    }

    return {
        "product_id": search_query.lower().replace(" ", "_"),
        "source": "cardmarket",
        "captured_at": now.isoformat(),
        "sold_price_avg": round(trimmed_avg, 2),
        "sold_price_median": round(median, 2),
        "sold_count_30d": None,
        "active_listings": len(priced),
        "sell_through": None,
        "lowest_ask": round(min(lows), 2) if lows else None,
        "currency": "EUR",
        "raw_json": json.dumps(raw),
        "_n_matched": len(priced),
        "_trend_vs_low": best.get("trendVsLowPct"),
        "_momentum_30": best.get("momentum30Pct"),
        "_expansion": best.get("expansionName"),
    }