import os, requests
from datetime import datetime

APIFY = os.environ["APIFY_TOKEN"]
ACTOR = "daddyapi~vinted-scraper"


def fetch_vinted(query, domain="fr", count=50):
    """Vinted via Apify (temporaire en attendant une solution gratuite)."""
    url = (f"https://api.apify.com/v2/acts/{ACTOR}"
           f"/run-sync-get-dataset-items?token={APIFY}")
    payload = {"searchQuery": query, "domain": domain, "maxItems": count}
    try:
        r = requests.post(url, json=payload, timeout=300)
    except Exception as e:
        print(f"[vinted] exception reseau : {e}", flush=True)
        return None
    if r.status_code != 200:
        print(f"[vinted] HTTP {r.status_code} : {r.text[:200]}", flush=True)
        return None
    items = r.json()
    if not items:
        return None
    prices = []
    for it in items:
        p = it.get("price") or it.get("priceEur")
        if p is None:
            continue
        try:
            prices.append(float(str(p).replace("€", "").replace(",", ".").strip()))
        except (ValueError, TypeError):
            continue
    if not prices:
        return None
    prices_sorted = sorted(prices)
    n = len(prices_sorted)
    median = prices_sorted[n // 2]
    k = max(1, n // 10)
    trimmed = prices_sorted[k:n-k] if n > 2*k else prices_sorted
    trimmed_avg = sum(trimmed) / len(trimmed)
    return {
        "product_id": query.lower().replace(" ", "_"),
        "source": "vinted_fr",
        "captured_at": datetime.utcnow().isoformat(),
        "sold_price_avg": round(trimmed_avg, 2),
        "sold_price_median": round(median, 2),
        "sold_count_30d": None,
        "active_listings": n,
        "sell_through": None,
        "lowest_ask": round(min(prices), 2),
        "currency": "EUR",
        "raw_json": None,
        "_n_listings": n,
    }