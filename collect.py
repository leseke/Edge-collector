import os
from connectors.ebay import fetch_sold
from storage import init_db, insert_snapshots

WATCHLIST = [
    {"id": "lorcana_hyperia_city", "query": "Lorcana Hyperia City booster box"},
    {"id": "lego_77073",           "query": "LEGO 77073 Fortnite Battle Bus"},
    {"id": "lego_75639",           "query": "LEGO 75639 Going Merry One Piece"},
    {"id": "lego_21371",           "query": "LEGO 21371 Wallace Gromit"},
    {"id": "riftbound_radiance",   "query": "Riftbound Radiance booster box"},
    {"id": "gundam_card_game",     "query": "Gundam Card Game booster box"},
]

def run():
    init_db()
    results = []
    for item in WATCHLIST:
        try:
            snap = fetch_sold(item["query"])
            if snap:
                snap["product_id"] = item["id"]
                results.append(snap)
                print(f"[eBay] {item['id']}: {snap['sold_count_30d']} ventes/30j, "
                      f"median {snap['sold_price_median']:.2f} {snap['currency']}")
        except Exception as e:
            print(f"[eBay] {item['id']} ERROR: {e}")

    if results:
        insert_snapshots([_flatten(r) for r in results])
        print(f"\n{len(results)} snapshots insérés dans storage.db")

def _flatten(s):
    return (s["product_id"], s["source"], s["captured_at"],
            s["sold_price_avg"], s["sold_price_median"],
            s["sold_count_30d"], s["active_listings"],
            s["sell_through"], s["lowest_ask"],
            s["currency"], s["raw_json"])

if __name__ == "__main__":
    run()
