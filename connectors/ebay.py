import os, requests
from datetime import datetime

APIFY = os.environ["APIFY_TOKEN"]
ACTOR = "tnodes~ebay-sold-scraper"

def fetch_sold(query, days=90, count=200, condition="any"):
    url = (f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items"
           f"?token={APIFY}")
    payload = {
        "keyword": query,
        "condition": condition,
        "daysToScrape": min(days, 90),
        "count": count,
    }
    r = requests.post(url, json=payload, timeout=300)
    r.raise_for_status()
    items = r.json()

    prices = [it["soldPrice"] for it in items if it.get("soldPrice")]
    if not prices:
        return None

    prices_sorted = sorted(prices)
    median = prices_sorted[len(prices_sorted)//2]

    return {
        "product_id": query.lower().replace(" ", "_"),
        "source": "ebay_fr",
        "captured_at": datetime.utcnow().isoformat(),
        "sold_price_avg": sum(prices)/len(prices),
        "sold_price_median": median,
        "sold_count_30d": sum(1 for it in items
                              if _days_ago(it.get("endedAt")) <= 30),
        "active_listings": None,
        "sell_through": None,
        "lowest_ask": None,
        "currency": items[0].get("soldCurrency", "EUR"),
        "raw_json": None,
    }

def _days_ago(iso_date):
    if not iso_date:
        return 999
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return (datetime.now(dt.tzinfo) - dt).days
    except Exception:
        return 999
