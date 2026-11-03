"""Uniform status-aware entry points for EDGE market-data connectors.

The dispatcher preserves each connector's legacy snapshot shape and returns
its privacy-safe ConnectorResult beside it. Ambiguous legacy None values stay
UNKNOWN; only adapters with positive completion evidence may report a clean
zero-result.
"""
from connectors.result import ConnectorResult, completed_query, failed_query


def fetch_scavio_with_status(query, gl="fr", hl="fr", limit=10):
    """Return (legacy Scavio snapshot, sanitized outcome)."""
    from connectors.scavio import fetch_scavio_offers

    try:
        snapshot = fetch_scavio_offers(
            query, gl=gl, hl=hl, limit=limit, raise_errors=True
        )
    except Exception as exc:
        return None, failed_query(exc)
    if snapshot is None:
        return None, completed_query(0)

    evidence_count = snapshot.get("n_offers")
    if isinstance(evidence_count, bool) or not isinstance(evidence_count, int) or evidence_count < 1:
        evidence_count = 1
    return snapshot, completed_query(evidence_count)


def fetch_source_with_status(provider, item):
    """Dispatch one configured check to its status-aware connector adapter.

    `item` is one watchlist record. This function makes no scheduling claim:
    NOT_SCHEDULED is decided by the source plan, not by a connector call.
    """
    if not isinstance(provider, str) or not provider.strip():
        raise ValueError("provider must be a non-empty string")
    if not isinstance(item, dict):
        raise ValueError("source item must be an object")

    if provider == "ebay":
        from connectors.ebay import fetch_sold_with_status

        result = fetch_sold_with_status(
            item["query"], must_all=item.get("must_all"),
            must_any=item.get("must_any"), count=100,
        )
    elif provider == "cardmarket":
        from connectors.cardmarket import fetch_cardmarket_with_status

        result = fetch_cardmarket_with_status(
            game=item["game"], search_query=item["search_query"],
            product_type=item.get("product_type", "sealed"),
            must_all=item.get("must_all"), must_any=item.get("must_any"),
            must_not=item.get("must_not"),
        )
    elif provider == "trends":
        from connectors.trends_spy import fetch_trends_spy_with_status

        result = fetch_trends_spy_with_status(item["keyword"])
    elif provider == "reddit":
        from connectors.reddit import fetch_reddit_with_status

        result = fetch_reddit_with_status(
            item["subreddit"], item["query"], limit=25
        )
    elif provider == "scavio":
        result = fetch_scavio_with_status(item["query"], gl="fr", hl="fr", limit=10)
    else:
        raise ValueError("unsupported source provider")

    if not isinstance(result, tuple) or len(result) != 2:
        raise TypeError("status adapter must return (snapshot, ConnectorResult)")
    snapshot, outcome = result
    if not isinstance(outcome, ConnectorResult):
        raise TypeError("status adapter returned an invalid ConnectorResult")
    if snapshot is not None and not isinstance(snapshot, dict):
        raise TypeError("connector snapshot must be an object or None")
    return snapshot, outcome
