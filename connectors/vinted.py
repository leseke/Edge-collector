import os
from datetime import datetime

# Import resilient
try:
    from vinted import Vinted
    VINTED_AVAILABLE = True
except ImportError:
    VINTED_AVAILABLE = False
    print("[vinted] module 'vinted-api-wrapper' non installe", flush=True)


def fetch_vinted(query, domain="fr", count=50):
    """Recherche des annonces Vinted via vinted-api-wrapper."""
    if not VINTED_AVAILABLE:
        return None
    try:
        vinted = Vinted(domain=domain)
        # L'API attend une URL de recherche
        search_url = f"https://www.vinted.{domain}/catalog?search_text={query}"
        items = vinted.items.search(search_url, count, 1)
    except Exception as e:
        print(f"[vinted] exception : {e}", flush=True)
        return None

    if not items:
        print(f"[vinted] {query} : aucun item", flush=True)
        return None

    prices = []
    for it in items:
        p = getattr(it, "price", None) or getattr(it, "price_eur", None)
        if p is None:
            continue
        try:
            prices.append(float(str(p).replace("€", "").replace(",", ".").strip()))
        except (ValueError, TypeError):
            continue

    if not prices:
        print(f"[vinted] aucun prix sur {len(items)} items", flush=True)
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