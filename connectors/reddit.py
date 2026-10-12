import time
import requests
from datetime import datetime, timezone

BASE_URL = "https://arctic-shift.photon-reddit.com/api"

# Delai entre deux requetes Arctic Shift (en secondes)
# L'archive est maintenue par des benevoles, il faut y aller doucement
REQUEST_DELAY = 12

_last_call = [0.0]


def _wait():
    now = time.time()
    elapsed = now - _last_call[0]
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    _last_call[0] = time.time()


def _try_fetch(url, params, retries=2):
    """Appel HTTP avec retry automatique en cas de 422 (timeout server)."""
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, params=params, timeout=60)
        except Exception as e:
            print(f"[reddit] exception reseau (essai {attempt+1}) : {e}", flush=True)
            time.sleep(5)
            continue
        if r.status_code == 200:
            return r
        if r.status_code == 422 and attempt < retries:
            print(f"[reddit] 422 timeout serveur, retry dans 8s (essai {attempt+1})", flush=True)
            time.sleep(8)
            continue
        # Autre erreur
        return r
    return None


def fetch_reddit(subreddit, query, limit=25):
    """Recupere les posts Reddit via l'archive publique Arctic Shift.

    Arctic Shift accepte les requetes depuis n'importe quelle IP mais
    rate-limite si on envoie trop de requetes en peu de temps.
    """
    _wait()

    url = f"{BASE_URL}/posts/search"
    params = {
        "subreddit": subreddit,
        "title": query,
        "limit": min(limit, 100),
        "sort": "desc",
    }

    r = _try_fetch(url, params, retries=2)
    if r is None:
        print(f"[reddit] r/{subreddit} '{query}' : echec apres retries", flush=True)
        return None
    if r.status_code != 200:
        print(f"[reddit] HTTP {r.status_code} sur r/{subreddit} '{query}' : {r.text[:200]}", flush=True)
        return None

    try:
        data = r.json()
    except Exception as e:
        print(f"[reddit] reponse non-JSON : {e}", flush=True)
        return None

    posts = data.get("data", [])
    if not posts:
        print(f"[reddit] r/{subreddit} '{query}' : aucun post", flush=True)
        return None

    scores = []
    comments = []
    recent_30d = 0
    now = datetime.now(timezone.utc)

    for p in posts:
        s = p.get("score")
        if s is not None:
            scores.append(s)
        c = p.get("num_comments")
        if c is not None:
            comments.append(c)
        created = p.get("created_utc")
        if created:
            try:
                dt = datetime.fromtimestamp(created, tz=timezone.utc)
                if (now - dt).days <= 30:
                    recent_30d += 1
            except Exception:
                pass

    avg_score = sum(scores) / len(scores) if scores else 0
    avg_comments = sum(comments) / len(comments) if comments else 0

    return {
        "product_id": f"reddit_{subreddit}_{query}".lower().replace(" ", "_"),
        "source": "reddit_arctic",
        "captured_at": now.isoformat(),
        "sold_price_avg": None,
        "sold_price_median": None,
        "sold_count_30d": None,
        "active_listings": len(posts),
        "sell_through": None,
        "lowest_ask": None,
        "currency": None,
        "raw_json": None,
        "reddit_total": len(posts),
        "reddit_recent_30d": recent_30d,
        "reddit_avg_score": round(avg_score, 1),
        "reddit_avg_comments": round(avg_comments, 1),
    }