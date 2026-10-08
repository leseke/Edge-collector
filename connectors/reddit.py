import os
from datetime import datetime
from redd import Redd


def fetch_reddit(subreddit, query, limit=50):
    """Surveille un subreddit pour un mot-clé donné."""
    try:
        with Redd() as r:
            results = r.search(
                query,
                subreddit=subreddit,
                limit=limit,
            )
            posts = list(results)
    except Exception as e:
        print(f"[reddit] exception : {e}", flush=True)
        return None

    if not posts:
        print(f"[reddit] {subreddit}/{query} : aucun post", flush=True)
        return None

    n_posts = len(posts)
    scores = [p.score for p in posts if hasattr(p, "score")]
    comments = [p.num_comments for p in posts if hasattr(p, "num_comments")]

    avg_score = sum(scores) / len(scores) if scores else 0
    avg_comments = sum(comments) / len(comments) if comments else 0

    # Le "momentum" est estimé par la part de posts récents
    now = datetime.utcnow()
    recent_posts = 0
    for p in posts:
        if hasattr(p, "created_utc"):
            dt = datetime.utcfromtimestamp(p.created_utc)
            if (now - dt).days <= 30:
                recent_posts += 1

    return {
        "product_id": f"reddit_{subreddit}_{query}".lower().replace(" ", "_"),
        "source": "reddit",
        "captured_at": datetime.utcnow().isoformat(),
        "sold_price_avg": None,
        "sold_price_median": None,
        "sold_count_30d": None,
        "active_listings": n_posts,
        "sell_through": None,
        "lowest_ask": None,
        "currency": None,
        "raw_json": None,
        "reddit_avg_score": round(avg_score, 1),
        "reddit_avg_comments": round(avg_comments, 1),
        "reddit_recent_30d": recent_posts,
        "reddit_total": n_posts,
    }