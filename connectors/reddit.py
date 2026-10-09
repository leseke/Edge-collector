from datetime import datetime, timezone

# Import resilient : si la bibliotheque change ou manque, on desactive
try:
    from redd import Redd
    REDD_AVAILABLE = True
except ImportError:
    REDD_AVAILABLE = False
    print("[reddit] module 'redd' non installe, connecteur desactive", flush=True)


# Rate limit : on fait une pause entre chaque appel pour eviter les 429
REQUEST_DELAY = 6
_last_call = [0.0]


def _wait():
    import time
    now = time.time()
    elapsed = now - _last_call[0]
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    _last_call[0] = time.time()


def fetch_reddit(subreddit, query, limit=30):
    """Recupere les posts Reddit via la bibliotheque 'redd'.

    Retourne un snapshot normalise, ou None en cas d'echec.
    Le module est concu pour ne jamais faire planter le pipeline.
    """
    if not REDD_AVAILABLE:
        return None

    _wait()

    try:
        with Redd() as r:
            # L'API de 'redd' peut varier selon la version.
            # On essaie plusieurs signatures et on garde la premiere qui marche.
            posts = None
            errors = []

            # Tentative 1 : search(query, subreddit=..., limit=...)
            try:
                posts = list(r.search(query, subreddit=subreddit, limit=limit))
            except TypeError as e1:
                errors.append(f"signature 1 : {e1}")

            # Tentative 2 : search(query, limit=...) puis filtre
            if posts is None:
                try:
                    posts = list(r.search(query, limit=limit))
                except TypeError as e2:
                    errors.append(f"signature 2 : {e2}")

            # Tentative 3 : r.subreddit(name).search(...)
            if posts is None:
                try:
                    posts = list(r.subreddit(subreddit).search(query, limit=limit))
                except Exception as e3:
                    errors.append(f"signature 3 : {e3}")

            if posts is None:
                print(f"[reddit] r/{subreddit} '{query}' : toutes les signatures ont echoue", flush=True)
                for err in errors:
                    print(f"   - {err}", flush=True)
                return None

    except Exception as e:
        print(f"[reddit] exception r/{subreddit} '{query}' : {e}", flush=True)
        return None

    if not posts:
        print(f"[reddit] r/{subreddit} '{query}' : aucun post", flush=True)
        return None

    scores = []
    comments = []
    recent_30d = 0
    now = datetime.now(timezone.utc)

    for p in posts:
        s = getattr(p, "score", None)
        if s is None:
            s = getattr(p, "ups", None)
        if s is not None:
            scores.append(s)

        c = getattr(p, "num_comments", None)
        if c is not None:
            comments.append(c)

        created = getattr(p, "created_utc", None)
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
        "source": "reddit",
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