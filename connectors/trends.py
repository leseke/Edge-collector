import os, requests
from datetime import datetime

APIFY = os.environ["APIFY_TOKEN"]
ACTOR = "apify~google-trends-scraper"


def fetch_trends(keyword, geo="FR", timeframe="today 12-m"):
    """Recupere l'interet Google Trends pour un mot-cle.
    Retourne l'acceleration (recent vs precedent) et le niveau actuel.
    """
    url = (f"https://api.apify.com/v2/acts/{ACTOR}"
           f"/run-sync-get-dataset-items?token={APIFY}")
    payload = {
        "searchTerms": [keyword],
        "geo": geo,
        "timeRange": timeframe,
    }
    r = requests.post(url, json=payload, timeout=180)
    r.raise_for_status()
    data = r.json()
    if not data:
        return None

    # La reponse contient timelineData
    timeline = data[0].get("timelineData", []) if isinstance(data, list) else []
    if not timeline:
        return None

    values = [int(d.get("value", [0])[0]) for d in timeline if d.get("value")]
    if not values:
        return None

    # Acceleration : derniers 3 mois vs 3 mois precedents
    if len(values) >= 24:
        recent = values[-12:]
        older = values[-24:-12]
    elif len(values) >= 12:
        recent = values[-6:]
        older = values[-12:-6]
    else:
        recent = values[-3:]
        older = values[:len(values)//2]

    avg_recent = sum(recent) / len(recent) if recent else 0
    avg_older = sum(older) / len(older) if older else 0

    if avg_older > 0:
        acceleration = avg_recent / avg_older
    else:
        acceleration = 1.0

    now = datetime.utcnow()
    return {
        "product_id": keyword.lower().replace(" ", "_"),
        "source": "google_trends_fr",
        "captured_at": now.isoformat(),
        "sold_price_avg": None,
        "sold_price_median": None,
        "sold_count_30d": None,
        "active_listings": None,
        "sell_through": None,
        "lowest_ask": None,
        "currency": None,
        "raw_json": None,
        "trend_recent_avg": round(avg_recent, 1),
        "trend_older_avg": round(avg_older, 1),
        "trend_acceleration": round(acceleration, 2),
    }