import os
from datetime import datetime, timezone

try:
    from scavio import ScavioClient
    SCAVIO_AVAILABLE = True
except ImportError:
    SCAVIO_AVAILABLE = False
    print("[scavio] module 'scavio' non installe", flush=True)

SCAVIO_API_KEY = os.environ.get("SCAVIO_API_KEY")


def fetch_scavio_offers(query, gl="fr", hl="fr", limit=10):
    """Recherche les offres retail FR via Google Shopping (Scavio).

    Retourne un snapshot normalise avec la liste des offres, ou None.
    """
    if not SCAVIO_AVAILABLE:
        print("[scavio] module non disponible", flush=True)
        return None
    if not SCAVIO_API_KEY:
        print("[scavio] SCAVIO_API_KEY absent", flush=True)
        return None

    try:
        client = ScavioClient(api_key=SCAVIO_API_KEY)
        res = client.google.shopping(
            query=query,
            gl=gl,
            hl=hl,
            google_domain="google.fr",
        )
    except Exception as e:
        print(f"[scavio] exception sur '{query}' : {e}", flush=True)
        return None

    shopping_results = res.get("shopping_results", [])
    if not shopping_results:
        print(f"[scavio] '{query}' : aucun resultat", flush=True)
        return None

    offers = []
    for item in shopping_results[:limit]:
        price_raw = item.get("price")
        price_eur = None
        if price_raw:
            try:
                # Format possible : "92,99 €" ou "92.99"
                cleaned = str(price_raw).replace("€", "").replace(",", ".").strip()
                price_eur = float(cleaned)
            except (ValueError, TypeError):
                pass

        offers.append({
            "title": item.get("title"),
            "price_eur": price_eur,
            "price_raw": price_raw,
            "seller": item.get("seller"),
            "catalog_id": item.get("catalog_id"),
            "product_link": item.get("product_link"),
        })

    # Trie par prix croissant (les None à la fin)
    offers.sort(key=lambda o: (o["price_eur"] is None, o["price_eur"] or 0))

    prices = [o["price_eur"] for o in offers if o["price_eur"] is not None]

    return {
        "product_id": query.lower().replace(" ", "_"),
        "source": "scavio_google_shopping",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "offers": offers,
        "n_offers": len(offers),
        "min_price_eur": min(prices) if prices else None,
        "max_price_eur": max(prices) if prices else None,
    }