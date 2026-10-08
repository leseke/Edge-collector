from datetime import datetime

try:
    from redd import Redd
    REDD_AVAILABLE = True
except ImportError:
    REDD_AVAILABLE = False
    print("[reddit] module 'redd' non installe, connecteur desactive", flush=True)


def fetch_reddit(subreddit, query, limit=30):
    if not REDD_AVAILABLE:
        return None
    try:
        with Redd() as r:
            posts = list(r.search(query, limit=limit))
    except Exception as e:
        print(f"[reddit] exception : {e}", flush=True)
        return None

    if not posts:
        print(f"[reddit] {query} : aucun post", flush=True)
        return None

    scores = [p.score for p in posts if hasattr(p, "score")]
    comments = [p.num_comments for p in posts if hasattr(p, "num_comments")]
    avg_score = sum(scores) / len(scores) if scores else 0
    avg_comments = sum(comments) / len(comments) if comments else 0

    now = datetime.utcnow()
    recent = 0
    for p in posts:
        if hasattr(p, "created_utc"):
            dt = datetime.utcfromtimestamp(p.created_utc)
            if (now - dt).days <= 30:
                recent += 1

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
        "reddit_avg_score": round(avg_score, 1),
        "reddit_avg_comments": round(avg_comments, 1),
        "reddit_recent_30d": recent,
        "reddit_total": len(posts),
    }