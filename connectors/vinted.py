import asyncio
from datetime import datetime
from vinted_api_kit import VintedClient


async def _search_vinted(query, domain="fr", count=50):
    async with VintedClient(domain=domain) as client:
        items = await client.search_items(query, per_page=count)
        return items


def fetch_vinted(query, domain="fr", count=50):
    """Recherche des annonces Vinted via vinted-api-kit."""
    try:
        items = asyncio.run(_search_vinted(query, domain, count))
    except Exception as e:
        print(f"[vinted] exception : {e}", flush=True)
        return None

    if not items:
        print(f"[vinted] {query} : aucun item", flush=True)
        return None

    prices = []
    for it in items:
        price = getattr(it, "price", None) or getattr(it, "price_eur", None)
        if price is None:
            continue
        try:
            prices.append(float(price))
        except (ValueError, TypeError):
            continue

    if not prices:
        print(f"[vinted] aucun prix sur {len(items)} items", flush=True)
        return None

    prices_sorted = sorted(prices)
    n = len(prices_sorted)
    median = prices_sorted[n // 2]
    k = max(1, n // 10)
    trimmed = prices_sorted[k:n - k] if n > 2 * k else prices_sorted
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