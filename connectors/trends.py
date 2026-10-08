import os, requests
from datetime import datetime

APIFY = os.environ["APIFY_TOKEN"]
ACTOR = "apify~google-trends-scraper"


def fetch_trends(keyword, geo="FR", timeframe="today 12-m"):
    url = (f"https://api.apify.com/v2/acts/{ACTOR}"
           f"/run-sync-get-dataset-items?token={APIFY}")
    payload = {"searchTerms": [keyword]}
    r = requests.post(url, json=payload, timeout=300)
    if r.status_code != 200:
        print(f"[trends] HTTP {r.status_code} - {r.text[:200]}", flush=True)
        return None

    data = r.json()
    if not data or not isinstance(data, list):
        print("[trends] reponse invalide", flush=True)
        return None

    first = data[0]
    timeline = first.get("interestOverTime_timelineData", [])
    if not timeline:
        timeline = first.get("timelineData", [])
    if not timeline:
        print("[trends] pas de timeline", flush=True)
        return None

    values = []
    for d in timeline:
        v = d.get("value")
        if v and isinstance(v, list) and len(v) > 0:
            try:
                values.append(int(v[0]))
            except (ValueError, TypeError):
                continue
    if not values:
        return None

    if len(values) >= 24:
        recent, older = values[-12:], values[-24:-12]
    elif len(values) >= 12:
        recent, older = values[-6:], values[-12:-6]
    else:
        recent, older = values[-3:], values[:len(values)//2]

    avg_recent = sum(recent) / len(recent) if recent else 0
    avg_older = sum(older) / len(older) if older else 0
    acceleration = avg_recent / avg_older if avg_older > 0 else 1.0

    return {
        "product_id": keyword.lower().replace(" ", "_"),
        "source": "google_trends_fr",
        "captured_at": datetime.utcnow().isoformat(),
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