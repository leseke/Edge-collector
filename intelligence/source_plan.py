"""Stable, per-query source plan for one collector execution.

This is an execution plan, not a scheduler record: it does not invent a
scheduled_at timestamp or a continuity window.
"""


def build_source_plan(config, watchlist, trends_watch, reddit_watch, scavio_watch):
    """Return enabled and disabled check IDs without making network requests."""
    if not isinstance(config, dict):
        raise ValueError("config must be an object")

    checks = []
    for item in watchlist:
        checks.append((item["id"], item["source"]))
    for item in trends_watch:
        checks.append((item["id"], "trends"))
    for item in reddit_watch:
        checks.append((item["id"], "reddit"))
    for item in scavio_watch:
        checks.append((item["id"], "scavio"))

    seen = set()
    enabled_ids = []
    disabled_ids = []
    providers = {}
    for check_id, provider in checks:
        if not isinstance(check_id, str) or not check_id.strip():
            raise ValueError("source check ID must be a non-empty string")
        if not isinstance(provider, str) or not provider.strip():
            raise ValueError("source provider must be a non-empty string")
        if check_id in seen:
            raise ValueError("duplicate source check ID")
        seen.add(check_id)
        providers[check_id] = provider
        target = enabled_ids if config.get("enabled_sources", {}).get(provider, True) else disabled_ids
        target.append(check_id)

    return {
        "expected_sources": enabled_ids,
        "not_scheduled_sources": disabled_ids,
        "providers": providers,
    }
