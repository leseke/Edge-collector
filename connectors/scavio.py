import os
from datetime import datetime, timezone

try:
    from scavio import ScavioClient
    SCAVIO_AVAILABLE = True
except ImportError:
    SCAVIO_AVAILABLE = False
    print("[scavio] module 'scavio' non installe", flush=True)

SCAVIO_API_KEY = os.environ.get("SCAVIO_API_KEY")


def parse_price_eur(raw):
    """Parse un prix affiche en EUR. Retourne None si ambigu ou non EUR.

    Gere "92,99 €", "92.99", "1 299,99 €" (espaces fines), "1.299,99 €",
    "1,299.99". Refuse les devises autres que l'euro.
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return float(raw) if raw > 0 else None
    s = str(raw).strip()
    if any(c in s for c in ("$", "£", "¥", "USD", "GBP", "CHF")):
        return None
    s = s.replace("€", "").replace("EUR", "")
    for sp in ("\u00a0", "\u202f", "\u2009", " "):
        s = s.replace(sp, "")
    s = s.strip()
    if not s or any(c not in "0123456789.," for c in s):
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        head, _, tail = s.rpartition(",")
        s = (head.replace(",", "") + "." + tail) if len(tail) != 3 or not head else s.replace(",", "")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    try:
        v = float(s)
    except ValueError:
        return None
    return v if v > 0 else None


def fetch_scavio_offers(query, gl="fr", hl="fr", limit=10, raise_errors=False):
    """Recherche les offres retail FR via Google Shopping (Scavio).

    Retourne un snapshot normalise avec la liste des offres, ou None.
    """
    # raise_errors=True (Discovery) : un echec technique leve une exception
    # au lieu d'etre confondu avec "aucun resultat".
    if not SCAVIO_AVAILABLE:
        print("[scavio] module non disponible", flush=True)
        if raise_errors:
            raise RuntimeError("module scavio non installe")
        return None
    if not SCAVIO_API_KEY:
        print("[scavio] SCAVIO_API_KEY absent", flush=True)
        if raise_errors:
            raise RuntimeError("SCAVIO_API_KEY absent")
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
        print(f"[scavio] exception sur '{query}' : {type(e).__name__}", flush=True)
        if raise_errors:
            raise
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
            price_eur = parse_price_eur(price_raw)

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