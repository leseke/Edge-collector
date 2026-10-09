import time
from datetime import datetime, timezone

try:
    from trendspy import Trends
    TRENDSPY_AVAILABLE = True
except ImportError:
    TRENDSPY_AVAILABLE = False
    print("[trends] module 'trendspy' non installe", flush=True)


# Delai entre deux requetes Google Trends (en secondes)
# Augmente si Google continue a rate-limiter
REQUEST_DELAY = 20


def fetch_trends_spy(keyword, geo="FR", timeframe="today 12-m"):
    """Recupere l'acceleration Google Trends via trendspy."""
    if not TRENDSPY_AVAILABLE:
        return None

    time.sleep(REQUEST_DELAY)

    try:
        tr = Trends(request_delay=4.0)
        df = tr.interest_over_time(
            [keyword],
            timeframe=timeframe,
            geo=geo,
        )
    except Exception as e:
        print(f"[trends] exception sur '{keyword}' : {e}", flush=True)
        return None

    if df is None or len(df) == 0:
        print(f"[trends] '{keyword}' : aucune donnee", flush=True)
        return None

    try:
        values = df[keyword].tolist()
    except KeyError:
        col = df.columns[0]
        values = df[col].tolist()

    if not values:
        return None

    n = len(values)
    if n >= 24:
        recent = values[-12:]
        older = values[-24:-12]
    elif n >= 12:
        recent = values[-6:]
        older = values[-12:-6]
    else:
        recent = values[-3:]
        older = values[: max(1, n // 2)]

    avg_recent = sum(recent) / len(recent) if recent else 0
    avg_older = sum(older) / len(older) if older else 0

    if avg_older > 0:
        acceleration = round(avg_recent / avg_older, 2)
    else:
        acceleration = None

    if acceleration is None:
        statut = f"pas de base (recent {avg_recent:.1f}, passe vide)"
    elif acceleration >= 1.5:
        statut = f"ACCELERATION FORTE x{acceleration}"
    elif acceleration >= 1.2:
        statut = f"acceleration x{acceleration}"
    elif acceleration >= 0.9:
        statut = f"stable x{acceleration}"
    else:
        statut = f"deceleration x{acceleration}"

    return {
        "product_id": keyword.lower().replace(" ", "_"),
        "source": "google_trends_fr",
        "captured_at": datetime.now(timezone.utc).isoformat(),
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
        "trend_acceleration": acceleration,
        "trend_statut": statut,
    }