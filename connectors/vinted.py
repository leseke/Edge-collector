import os, requests, json
from datetime import datetime

APIFY = os.environ["APIFY_TOKEN"]
ACTOR = "daddyapi~vinted-scraper"


def fetch_vinted(query, domain="fr", count=50):
    url = (f"https://api.apify.com/v2/acts/{ACTOR}"
           f"/run-sync-get-dataset-items?token={APIFY}")
    payload = {"searchQuery": query, "domain": domain, "maxItems": count}

    print(f"[vinted] POST {ACTOR} payload={payload}", flush=True)
    try:
        r = requests.post(url, json=payload, timeout=300)
    except Exception as e:
        print(f"[vinted] exception reseau : {e}", flush=True)
        return None

    print(f"[vinted] HTTP {r.status_code}", flush=True)
    if r.status_code != 200:
        print(f"[vinted] reponse erreur : {r.text[:300]}", flush=True)
        return None

    items = r.json()
    print(f"[vinted] type reponse : {type(items).__name__}", flush=True)

    if not items:
        print("[vinted] liste vide", flush=True)
        return None

    # Log la structure du premier item pour diagnostiquer
    if isinstance(items, list) and items:
        first = items[0]
        print(f"[vinted] cles 1er item : {list(first.keys())[:15]}", flush=True)

    prices = []
    for it in items:
        if not isinstance(it, dict):
            continue
        p = (it.get("price") or it.get("priceEur") or it.get("totalPrice")
             or it.get("price_amount"))
        if p is None:
            continue
        try:
            p_clean = str(p).replace("€", "").replace(",", ".").strip()
            prices.append(float(p_clean))
        except (ValueError, TypeError):
            continue

    if not prices:
        print(f"[vinted] aucun prix extrait sur {len(items)} items", flush=True)
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