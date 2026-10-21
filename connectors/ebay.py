import os, re, requests
from datetime import datetime, timedelta



def _apify_token():
    """Lecture differee : l'import ne plante plus sans token.
    L'absence de token devient une erreur explicite au moment de l'appel."""
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        raise RuntimeError("APIFY_TOKEN absent")
    return token
ACTOR = "caffein.dev~ebay-sold-listings"


def actor_input(query, count, days=90):
    """Format d'entree de l'acteur caffein.dev/ebay-sold-listings, aligne
    sur ses exemples publics ("keywords" liste + "count"). L'ancien format
    ("keyword"/"maxItems") ne correspondait pas a ces exemples. A confirmer
    au premier appel reel (le schema de l'acteur fait foi)."""
    return {"keywords": [query], "count": int(count), "daysToScrape": int(days),
            "ebaySite": "ebay.com", "itemCondition": "any"}


def fetch_sold(query, must_all=None, must_any=None, count=100,
               days_window=90):
    """Recherche eBay + filtre strict sur le titre.

    must_all : liste de mots qui DOIVENT tous etre dans le titre
    must_any : liste de mots dont AU MOINS UN doit etre dans le titre
    """
    must_all = [m.lower() for m in (must_all or [])]
    must_any = [m.lower() for m in (must_any or [])]

    # Token en en-tete (et non dans l'URL) : une erreur HTTP ne l'expose
    # plus dans les logs.
    url = f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items"
    headers = {"Authorization": f"Bearer {_apify_token()}"}
    payload = actor_input(query, count)

    r = requests.post(url, json=payload, headers=headers, timeout=300)
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


def fetch_sold_items(query, count=100):
    """Ventes conclues brutes (une entree par vente) pour Discovery.

    Pas de filtre de titre : c'est le pipeline Discovery qui identifie
    le produit. Retourne une liste (eventuellement vide) ; leve en cas
    d'erreur reseau ou d'authentification (jamais d'echec silencieux).
    """
    url = f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items"
    headers = {"Authorization": f"Bearer {_apify_token()}"}
    r = requests.post(url, json=actor_input(query, count),
                      headers=headers, timeout=300)
    r.raise_for_status()
    return r.json() or []
