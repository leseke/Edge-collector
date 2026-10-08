import os
import requests
from datetime import datetime

API_KEY = os.environ.get("TRENDSMCP_API_KEY")
ENDPOINT = "https://api.trendsmcp.ai/mcp"

def fetch_trends(keyword, geo="FR", timeframe="today 12-m"):
    """Récupère l'accélération Google Trends via l'API trendsmcp.ai."""
    if not API_KEY:
        print("[trends] TRENDSMCP_API_KEY absent", flush=True)
        return None

    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "google_trends_interest_over_time",
            "arguments": {
                "query": keyword,
                "geo": geo,
                "time_range": timeframe,
            },
        },
        "id": 1,
    }

    try:
        r = requests.post(
            ENDPOINT,
            json=payload,
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=60,
        )
    except Exception as e:
        print(f"[trends] exception réseau : {e}", flush=True)
        return None

    if r.status_code != 200:
        print(f"[trends] HTTP {r.status_code} - {r.text[:300]}", flush=True)
        return None

    data = r.json()
    result = data.get("result", {})
    content = result.get("content", [])
    if not content:
        print("[trends] pas de contenu dans la réponse", flush=True)
        return None

    # La réponse peut être du texte JSON ou un objet structuré
    timeline = []
    for c in content:
        if isinstance(c, dict) and c.get("type") == "text":
            try:
                inner = c.get("text", "[]")
                timeline = eval(inner) if isinstance(inner, str) else inner
            except Exception:
                pass
    if not timeline:
        print("[trends] timeline vide", flush=True)
        return None

    values = []
    for d in timeline:
        v = d.get("value")
        if v:
            try:
                values.append(int(v))
            except (ValueError, TypeError):
                continue

    if not values:
        return None

    if len(values) >= 24:
        recent, older = values[-12:], values[-24:-12]
    elif len(values) >= 12:
        recent, older = values[-6:], values[-12:-6]
    else:
        recent, older = values[-3:], values[:len(values) // 2]

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