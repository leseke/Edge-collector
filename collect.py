import os
from connectors.ebay import fetch_sold as fetch_ebay
from connectors.cardmarket import fetch_cardmarket
from storage import init_db, insert_snapshots

USD_TO_EUR = 0.92

WATCHLIST = [
    # --- LEGO via eBay ---
    {
        "id": "lego_77073",
        "source": "ebay",
        "query": "LEGO 77073",
        "must_all": ["77073"],
        "must_any": ["lego", "fortnite", "battle bus"],
        "target_buy": 60,
        "target_strong_buy": 50,
    },
    {
        "id": "lego_75639",
        "source": "ebay",
        "query": "LEGO 75639",
        "must_all": ["75639"],
        "must_any": ["lego", "one piece", "going merry"],
        "target_buy": 90,
        "target_strong_buy": 80,
    },
    {
        "id": "lego_21371",
        "source": "ebay",
        "query": "LEGO 21371",
        "must_all": ["21371"],
        "must_any": ["lego", "wallace", "gromit"],
        "target_buy": 85,
        "target_strong_buy": 70,
    },
    # --- TCG via Cardmarket ---
    {
        "id": "lorcana_hyperia_box",
        "source": "cardmarket",
        "game": "lorcana",
        "search_query": "Hyperia City",
        "must_all": ["hyperia"],
        "must_any": ["booster box", "display"],
        "must_not": ["case", "sleeve", "playmat", "bundle", "single"],
        "target_buy": 100,
        "target_strong_buy": 85,
    },
    {
        "id": "riftbound_radiance_box",
        "source": "cardmarket",
        "game": "riftbound",
        "search_query": "Radiance",
        "must_all": ["radiance"],
        "must_any": ["booster box", "display"],
        "must_not": ["case", "sleeve", "playmat", "bundle"],
        "target_buy": 110,
        "target_strong_buy": 100,
    },
    {
        "id": "one_piece_op18_box",
        "source": "cardmarket",
        "game": "onepiece",
        "search_query": "OP-18",
        "must_all": ["op-18"],
        "must_any": ["booster box", "display"],
        "must_not": ["case", "sleeve", "playmat"],
        "target_buy": 90,
        "target_strong_buy": 80,
    },
]


def evaluate_signal(prix_eur, item):
    strong = item.get("target_strong_buy")
    target = item.get("target_buy")
    if strong and prix_eur <= strong:
        return "STRONG_BUY", f"🔥🔥 ACHAT FORT : {prix_eur:.0f} EUR <= {strong} EUR"
    if target and prix_eur <= target:
        return "BUY", f"🔥 ACHAT : {prix_eur:.0f} EUR <= {target} EUR"
    if target:
        ecart = (prix_eur - target) / target * 100
        return "WAIT", f"⏸  ATTENDRE : {prix_eur:.0f} EUR > {target} EUR (+{ecart:.0f}%)"
    return "WATCH", f"👁  WATCH : {prix_eur:.0f} EUR"


def fetch_one(item):
    """Dispatche selon la source."""
    if item["source"] == "ebay":
        return fetch_ebay(
            item["query"],
            must_all=item.get("must_all"),
            must_any=item.get("must_any"),
            count=100,
        )
    if item["source"] == "cardmarket":
        return fetch_cardmarket(
            game=item["game"],
            search_query=item["search_query"],
            must_all=item.get("must_all"),
            must_any=item.get("must_any"),
            must_not=item.get("must_not"),
        )
    raise ValueError(f"source inconnue : {item['source']}")


def run():
    init_db()
    results = []
    alerts = []

    for item in WATCHLIST:
        try:
            snap = fetch_one(item)
            if not snap:
                print(f"[{item['source']}] {item['id']}: aucun resultat",
                      flush=True)
                continue

            snap["product_id"] = item["id"]
            results.append(snap)

            # Prix en EUR (conversion si eBay)
            prix_eur = snap["sold_price_median"]
            if item["source"] == "ebay":
                prix_eur *= USD_TO_EUR

            extra = ""
            if item["source"] == "cardmarket":
                tvl = snap.get("_trend_vs_low")
                m30 = snap.get("_momentum_30")
                extra = (f" | trendVsLow {tvl}%"
                         f" | momentum30 {m30}%")

            print(
                f"[{item['source']}] {item['id']}: "
                f"median {snap['sold_price_median']} {snap['currency']} | "
                f"low {snap['lowest_ask']} | "
                f"n={snap.get('_n_matched') or snap.get('_n_filtered')}"
                f"{extra}",
                flush=True
            )

            niveau, message = evaluate_signal(prix_eur, item)
            print(f"   {message}", flush=True)

            if niveau in ("BUY", "STRONG_BUY"):
                alerts.append({"id": item["id"], "niveau": niveau,
                               "prix_eur": prix_eur, "message": message})

        except Exception as e:
            print(f"[{item['source']}] {item['id']} ERROR: {e}", flush=True)

    if results:
        insert_snapshots([_flatten(r) for r in results])
        print(f"\n{len(results)} snapshots inseres dans storage.db", flush=True)

    print("\n=== RESUME ===", flush=True)
    if alerts:
        print(f"{len(alerts)} signal(aux) d'achat detecte(s) :", flush=True)
        for a in alerts:
            print(f"  - [{a['niveau']}] {a['id']} : {a['message']}",
                  flush=True)
    else:
        print("Aucun signal d'achat. Decision : CASH / ATTENDRE.", flush=True)


def _flatten(s):
    return (s["product_id"], s["source"], s["captured_at"],
            s["sold_price_avg"], s["sold_price_median"],
            s["sold_count_30d"], s["active_listings"],
            s["sell_through"], s["lowest_ask"],
            s["currency"], s["raw_json"])


if __name__ == "__main__":
    run()