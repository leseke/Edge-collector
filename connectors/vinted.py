import os, requests
from datetime import datetime

APIFY = os.environ["APIFY_TOKEN"]
ACTOR = "daddyapi~vinted-scraper"


def fetch_vinted(query, domain="fr", count=100):
    """Scrape les annonces Vinted pour un mot-cle.
    Retourne les stats de marche (prix moyen, median, volume).
    """
    url = (f"https://api.apify.com/v2/acts/{ACTOR}"
           f"/run-sync-get-dataset-items?token={APIFY}")
    payload = {
        "searchQuery": query,
        "domain": domain,
        "maxItems": count,
    }
    r = requests.post(url, json=payload, timeout=300)
    r.raise_for_status()
    items = r.json()
    if not items:
        return None

    prices = []
    for it in items:
        p = it.get("price") or it.get("priceEur")
        if p is None:
            continue
        try:
            prices.append(float(p))
        except (ValueError, TypeError):
            continue

    if not prices:
        return None

    prices_sorted = sorted(prices)
    n = len(prices_sorted)
    median = prices_sorted[n // 2]

    # Moyenne tronquee (enleve les 10% extremes)
    k = max(1, n // 10)
    trimmed = prices_sorted[k:n-k] if n > 2*k else prices_sorted
    trimmed_avg = sum(trimmed) / len(trimmed)

    # Nombre d'annonces sous la mediane = indicateur de tension
    below_median = sum(1 for p in prices if p < median)

    now = datetime.utcnow()
    return {
        "product_id": query.lower().replace(" ", "_"),
        "source": "vinted_fr",
        "captured_at": now.isoformat(),
        "sold_price_avg": round(trimmed_avg, 2),
        "sold_price_median": round(median, 2),
        "sold_count_30d": None,          # Vinted n'expose pas les ventes
        "active_listings": n,
        "sell_through": None,
        "lowest_ask": round(min(prices), 2),
        "currency": "EUR",
        "raw_json": None,
        "_n_listings": n,
        "_below_median": below_median,
    }