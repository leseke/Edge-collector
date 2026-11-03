"""Status adapters for legacy connectors whose public return shape is preserved."""

from connectors.result import completed_query, failed_query


def fetch_scavio_with_status(query, gl="fr", hl="fr", limit=10):
    """Return (legacy Scavio snapshot, sanitized outcome).

    Scavio's raise_errors=True mode makes a missing dependency, missing
    credential or request exception explicit. A successful empty shopping
    response returns None and is therefore a confirmed zero-result.
    """
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
