import os
import json
from datetime import datetime, timezone

from connectors.ebay import fetch_sold as fetch_ebay
from connectors.cardmarket import fetch_cardmarket
from connectors.trends_spy import fetch_trends_spy
from connectors.reddit import fetch_reddit
from connectors.telegram import send_message, format_alert, send_daily_digest
from storage import init_db, insert_snapshots
from edge_engine import load_config, load_portfolio, decide

USD_TO_EUR = 0.92


WATCHLIST = [
    {
        "id": "lego_77073",
        "name": "LEGO 77073 Fortnite Battle Bus",
        "emoji": "🚌",
        "image_url": "https://img.bricklink.com/ItemImage/SN/0/77073-1.png",
        "source": "ebay",
        "category": "flip",
        "query": "LEGO 77073",
        "must_all": ["77073"],
        "must_any": ["lego", "fortnite", "battle bus"],
        "target_buy": 60,
        "target_strong_buy": 50,
        "thesis": "Licence Fortnite extremement populaire aupres du public jeune adulte, set LEGO dont le retrait est souvent annonce peu de temps a l'avance.",
        "counter_thesis": "Aucun catalyseur date confirme. La production LEGO peut etre prolongee si les ventes restent fortes.",
        "invalidation": "Si LEGO prolonge au-dela de 2027, la these est morte. Si le prix median depasse 100 EUR, la fenetre est fermee.",
    },
    {
        "id": "lego_75639",
        "name": "LEGO 75639 Going Merry One Piece",
        "emoji": "⛵",
        "image_url": "https://img.bricklink.com/ItemImage/SN/0/75639-1.png",
        "source": "ebay",
        "category": "future_classic",
        "query": "LEGO 75639",
        "must_all": ["75639"],
        "must_any": ["lego", "one piece", "going merry"],
        "target_buy": 90,
        "target_strong_buy": 80,
        "thesis": "Premier set LEGO base sur One Piece, licence culte au Japon et en forte croissance en Europe.",
        "counter_thesis": "Le prix actuel du marche est deja eleve. La production pourrait durer plusieurs annees.",
        "invalidation": "Si LEGO sort une reedition amelioree du Going Merry, l'original perd sa valeur historique.",
    },
    {
        "id": "lego_21371",
        "name": "LEGO 21371 Wallace & Gromit",
        "emoji": "🧀",
        "image_url": "https://img.bricklink.com/ItemImage/SN/0/21371-1.png",
        "source": "ebay",
        "category": "future_classic",
        "query": "LEGO 21371",
        "must_all": ["21371"],
        "must_any": ["lego", "wallace", "gromit"],
        "target_buy": 85,
        "target_strong_buy": 70,
        "thesis": "Licence culte depuis les annees quatre-vingt-dix, public adulte nostalgique, format LEGO Ideas a tirage initial limite.",
        "counter_thesis": "Le marche europeen peut etre moins demande que le marche americain pour cette licence.",
        "invalidation": "Si LEGO prolonge la production au-dela de 2027, la these de rarete s'effondre.",
    },
    {
        "id": "lorcana_hyperia_box",
        "name": "Lorcana Hyperia City Booster Box",
        "emoji": "✨",
        "image_url": "",
        "source": "cardmarket",
        "category": "flip",
        "game": "lorcana",
        "search_query": "Hyperia City",
        "must_all": ["hyperia"],
        "must_any": ["booster box", "display"],
        "must_not": ["case", "sleeve", "playmat", "bundle", "single"],
        "target_buy": 100,
        "target_strong_buy": 85,
        "thesis": "Sortie officielle en octobre 2026, Disney et Pixar se croisent dans un set Lorcana.",
        "counter_thesis": "La sortie est trop recente pour avoir un historique de ventes secondaires fiables.",
        "invalidation": "Si Disney annonce une reimpression massive dans les six mois, la these de rarete est morte.",
    },
    {
        "id": "riftbound_radiance_box",
        "name": "Riftbound Radiance Booster Box",
        "emoji": "⚔️",
        "image_url": "",
        "source": "cardmarket",
        "category": "flip",
        "game": "riftbound",
        "search_query": "Radiance",
        "must_all": ["radiance"],
        "must_any": ["booster box", "display"],
        "must_not": ["case", "sleeve", "playmat", "bundle"],
        "target_buy": 110,
        "target_strong_buy": 100,
        "thesis": "Sortie en octobre 2026, nouveau jeu de Riot Games qui capitalise sur l'univers de League of Legends.",
        "counter_thesis": "Riot a un historique de reimpressions agressives quand un produit marche.",
        "invalidation": "Si Riot annonce une seconde impression dans les six mois, la these de rarete est morte.",
    },
]


TRENDS_WATCH = [
    {"keyword": "LEGO Fortnite", "id": "trends_lego_fortnite"},
    {"keyword": "LEGO Going Merry", "id": "trends_lego_goingmerry"},
    {"keyword": "LEGO Wallace Gromit", "id": "trends_lego_wallace"},
    {"keyword": "Lorcana Hyperia", "id": "trends_lorcana_hyperia"},
    {"keyword": "Riftbound", "id": "trends_riftbound"},
]


REDDIT_WATCH = [
    {"subreddit": "lego", "query": "Fortnite Battle Bus", "id": "reddit_lego_77073"},
    {"subreddit": "lego", "query": "Going Merry", "id": "reddit_lego_75639"},
    {"subreddit": "lego", "query": "Wallace Gromit", "id": "reddit_lego_21371"},
    {"subreddit": "Lorcana", "query": "Hyperia", "id": "reddit_lorcana_hyperia"},
    {"subreddit": "Riftbound", "query": "Radiance", "id": "reddit_riftbound"},
]


def fetch_one(item):
    if item["source"] == "ebay":
        return fetch_ebay(item["query"],
                          must_all=item.get("must_all"),
                          must_any=item.get("must_any"),
                          count=100)
    if item["source"] == "cardmarket":
        return fetch_cardmarket(game=item["game"],
                                search_query=item["search_query"],
                                must_all=item.get("must_all"),
                                must_any=item.get("must_any"),
                                must_not=item.get("must_not"))
    raise ValueError(f"source inconnue : {item['source']}")


def run():
    init_db()
    config = load_config()
    portfolio = load_portfolio()

    print(f"[config] capital mensuel : {config['capital_monthly']} EUR", flush=True)
    print(f"[config] capital engage : {config['capital_engaged']} EUR", flush=True)
    print(f"[config] positions en cours : {len(portfolio.get('positions', []))}", flush=True)

    results = []
    alerts = []
    digest = []
    radar_products = []
    trends_signals = []
    reddit_signals = []

    # --- Section 1 : Watchlist principale (prix) ---
    print("\n[main] === section prix ===", flush=True)
    for item in WATCHLIST:
        try:
            snap = fetch_one(item)
            if not snap:
                print(f"[{item['source']}] {item['id']} : aucun resultat", flush=True)
                radar_products.append({
                    "id": item["id"],
                    "name": item["name"],
                    "emoji": item.get("emoji", "?"),
                    "image_url": item.get("image_url", ""),
                    "source": item["source"],
                    "decision": "NO_DATA",
                    "price_eur": None,
                    "target_buy": item.get("target_buy"),
                    "target_strong_buy": item.get("target_strong_buy"),
                    "ecart_pct": None,
                    "allocation_eur": [0, 0],
                    "cycle_num": 0,
                    "cycle_label": "Inconnu",
                    "categorie": item.get("category", "flip").upper(),
                    "thesis": item.get("thesis", ""),
                    "counter_thesis": item.get("counter_thesis", ""),
                    "invalidation": item.get("invalidation", ""),
                })
                continue

            snap["product_id"] = item["id"]
            results.append(snap)

            prix_eur = snap["sold_price_median"]
            if item["source"] == "ebay":
                prix_eur *= USD_TO_EUR

            decision = decide(item, prix_eur, snap, config)

            print(f"[{item['source']}] {item['id']} : median {snap['sold_price_median']} {snap['currency']}", flush=True)
            print(f"   {decision['message']}", flush=True)
            print(f"   Cycle : {decision['cycle_num']}/7 ({decision['cycle_label']})", flush=True)
            if decision["allocation_eur"][1] > 0:
                print(f"   Allocation suggeree : {decision['allocation_eur'][0]} a {decision['allocation_eur'][1]} EUR", flush=True)

            radar_products.append({
                "id": item["id"],
                "name": item["name"],
                "emoji": item.get("emoji", "?"),
                "image_url": item.get("image_url", ""),
                "source": item["source"],
                "decision": decision["decision"],
                "price_eur": round(prix_eur, 2),
                "median": snap["sold_price_median"],
                "currency_src": snap["currency"],
                "low": snap.get("lowest_ask"),
                "n": snap.get("_n_matched") or snap.get("_n_filtered"),
                "target_buy": item.get("target_buy"),
                "target_strong_buy": item.get("target_strong_buy"),
                "ecart_pct": decision["ecart_pct"],
                "allocation_eur": decision["allocation_eur"],
                "cycle_num": decision["cycle_num"],
                "cycle_label": decision["cycle_label"],
                "categorie": decision["categorie"],
                "thesis": item.get("thesis", ""),
                "counter_thesis": item.get("counter_thesis", ""),
                "invalidation": item.get("invalidation", ""),
            })

            digest.append({
                "id": item["id"],
                "niveau": decision["decision"],
                "prix_eur": prix_eur,
                "source": item["source"],
            })

            if decision["decision"] in ("BUY", "STRONG_BUY"):
                alerts.append(item)
                send_message(format_alert(item, prix_eur,
                                          decision["decision"], snap))

        except Exception as e:
            print(f"[{item['source']}] {item['id']} ERREUR : {e}", flush=True)
            radar_products.append({
                "id": item["id"],
                "name": item["name"],
                "emoji": item.get("emoji", "?"),
                "image_url": item.get("image_url", ""),
                "source": item["source"],
                "decision": "ERROR",
                "price_eur": None,
                "target_buy": item.get("target_buy"),
                "target_strong_buy": item.get("target_strong_buy"),
                "ecart_pct": None,
                "allocation_eur": [0, 0],
                "cycle_num": 0,
                "cycle_label": "Inconnu",
                "categorie": item.get("category", "flip").upper(),
                "thesis": item.get("thesis", ""),
                "counter_thesis": item.get("counter_thesis", ""),
                "invalidation": item.get("invalidation", ""),
            })

    # --- Section 2 : Google Trends (gratuit via trendspy) ---
    print("\n[trends] === section Google Trends ===", flush=True)
    for item in TRENDS_WATCH:
        try:
            trend = fetch_trends_spy(item["keyword"])
            if trend:
                trend["product_id"] = item["id"]
                results.append(trend)
                acc = trend.get("trend_acceleration")
                acc_str = f"x{acc}" if acc is not None else "xNone"
                print(f"[trends] {item['id']} : acceleration {acc_str} "
                      f"(recent {trend['trend_recent_avg']} vs passe {trend['trend_older_avg']})",
                      flush=True)
                trends_signals.append({
                    "id": item["id"],
                    "keyword": item["keyword"],
                    "acceleration": acc,
                    "recent_avg": trend["trend_recent_avg"],
                    "older_avg": trend["trend_older_avg"],
                    "statut": trend.get("trend_statut", ""),
                })
            else:
                print(f"[trends] {item['id']} : aucun resultat", flush=True)
        except Exception as e:
            print(f"[trends] {item['id']} ERREUR : {e}", flush=True)

    # --- Section 3 : Reddit (gratuit via 'redd') ---
    print("\n[reddit] === section Reddit ===", flush=True)
    for item in REDDIT_WATCH:
        try:
            snap = fetch_reddit(item["subreddit"], item["query"], limit=25)
            if snap:
                snap["product_id"] = item["id"]
                results.append(snap)
                print(f"[reddit] {item['id']} : {snap['reddit_total']} posts, "
                      f"{snap['reddit_recent_30d']} recents 30j, "
                      f"score moy {snap['reddit_avg_score']}, "
                      f"comm moy {snap['reddit_avg_comments']}",
                      flush=True)
                reddit_signals.append({
                    "id": item["id"],
                    "subreddit": item["subreddit"],
                    "query": item["query"],
                    "total": snap["reddit_total"],
                    "recent_30d": snap["reddit_recent_30d"],
                    "avg_score": snap["reddit_avg_score"],
                    "avg_comments": snap["reddit_avg_comments"],
                })
            else:
                print(f"[reddit] {item['id']} : aucun resultat", flush=True)
        except Exception as e:
            print(f"[reddit] {item['id']} ERREUR : {e}", flush=True)

    # --- Section 4 : Ecriture radar.json ---
    n_buy = sum(1 for p in radar_products if p["decision"] in ("BUY", "STRONG_BUY"))
    n_wait = sum(1 for p in radar_products if p["decision"] == "WAIT")
    n_watch = sum(1 for p in radar_products if p["decision"] == "WATCH")
    n_nodata = sum(1 for p in radar_products if p["decision"] in ("NO_DATA", "ERROR"))

    capital_available = config["capital_max_available"] - config["capital_engaged"]

    radar = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": config,
        "summary": {
            "n_buy": n_buy,
            "n_wait": n_wait,
            "n_watch": n_watch,
            "n_nodata": n_nodata,
            "total": len(radar_products),
            "capital_available": capital_available,
            "capital_engaged": config["capital_engaged"],
            "capital_monthly": config["capital_monthly"],
            "decision": "CASH" if n_buy == 0 else f"{n_buy} SIGNAL",
        },
        "products": radar_products,
        "trends": trends_signals,
        "reddit": reddit_signals,
    }

    with open("radar.json", "w") as f:
        json.dump(radar, f, indent=2, ensure_ascii=False)
    print("\nradar.json ecrit", flush=True)

    if results:
        insert_snapshots([_flatten(r) for r in results])
        print(f"{len(results)} snapshots inseres dans storage.db", flush=True)

    send_daily_digest(digest)

    print("\n=== RESUME ===", flush=True)
    if alerts:
        print(f"{len(alerts)} signal ou signaux d'achat", flush=True)
    else:
        print("Aucun signal d'achat. Decision : CASH.", flush=True)


def _flatten(s):
    return (s["product_id"], s["source"], s["captured_at"],
            s["sold_price_avg"], s["sold_price_median"],
            s["sold_count_30d"], s["active_listings"],
            s["sell_through"], s["lowest_ask"],
            s["currency"], s["raw_json"])


if __name__ == "__main__":
    run()