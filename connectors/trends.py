import os, requests
from datetime import datetime

APIFY = os.environ["APIFY_TOKEN"]
ACTOR = "apify~google-trends-scraper"


def fetch_trends(keyword, geo="FR", timeframe="today 12-m"):
    url = (f"https://api.apify.com/v2/acts/{ACTOR}"
           f"/run-sync-get-dataset-items?token={APIFY}")
    payload = {"searchTerms": [keyword]}
    print(f"[trends] payload: {payload}", flush=True)
    r = requests.post(url, json=payload, timeout=180)
    print(f"[trends] HTTP {r.status_code}", flush=True)
    if r.status_code != 200:
        print(f"[trends] reponse: {r.text[:300]}", flush=True)
        return None
    data = r.json()
    if not data:
        print("[trends] reponse vide", flush=True)
        return None

    timeline = []
    if isinstance(data, list) and data:
        timeline = data[0].get("timelineData", [])
    if not timeline:
        print("[trends] pas de timelineData", flush=True)
        return None

    values = [int(d.get("value", [0])[0]) for d in timeline if d.get("value")]
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