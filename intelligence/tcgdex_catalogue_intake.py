"""Small bounded API intake using an injected HTTP client; no credentials or buying.

Transport must return (status, content_type, bytes); production callers supply
an approved network implementation with timeout and redirect protections.
"""
from intelligence.tcgdex_catalogue_review import inspect_tcgdex_sets
URL="https://api.tcgdex.net/v2/fr/sets"

def collect_tcgdex_fr(*, observed_at, transport):
    if not callable(transport):
        raise ValueError("approved transport required")
    status,content_type,body=transport(URL)
    if status!=200 or "json" not in content_type.lower():
        raise ValueError("unexpected API response")
    result=inspect_tcgdex_sets(body,observed_at=observed_at)
    result["requested_url"]=URL
    result["collection_mode"]="INJECTED_APPROVED_TRANSPORT"
    return result
