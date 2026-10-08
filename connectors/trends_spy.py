from datetime import datetime

try:
    from trendspy import Trends
    TRENDSPY_AVAILABLE = True
except ImportError:
    TRENDSPY_AVAILABLE = False
    print("[trends] module 'trendspy' non installe", flush=True)


def fetch_trends_spy(keyword, geo="FR", timeframe="today 12-m"):
    """Recupere l'acceleration Google Trends via trendspy.

    Retourne un dict normalise, ou None en cas d'echec.
    """
    if not TRENDSPY_AVAILABLE:
        return None

    try:
        tr = Trends()
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

    # Extraire les valeurs pour le mot-cle
    try:
        values = df[keyword].tolist()
    except KeyError:
        # si le nom de colonne differe legerement
        col = df.columns[0]
        values = df[col].tolist()

    if not values:
        return None

    # Acceleration : recent vs plus ancien
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