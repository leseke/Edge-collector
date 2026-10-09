from datetime import datetime, timezone

try:
    from redd import Redd
    REDD_AVAILABLE = True
except ImportError:
    REDD_AVAILABLE = False
    print("[reddit] module 'redd' non installe, connecteur desactive", flush=True)


def fetch_reddit(subreddit, query, limit=25):
    """Recupere les posts Reddit via la bibliotheque 'redd'."""
    if not REDD_AVAILABLE:
        return None

    try:
        with Redd() as r:
            posts = list(r.search_subreddit(subreddit, query, limit=limit))
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