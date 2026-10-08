import os
from connectors.ebay import fetch_sold
from storage import init_db, insert_snapshots

# Requetes precises : identifiants exacts, pas de mots parasites
WATCHLIST = [
    {"id": "lego_77073",         "query": "77073"},
    {"id": "lego_75639",         "query": "75639"},
    {"id": "lego_21371",         "query": "21371"},
    {"id": "lorcana_hyperia",    "query": "Hyperia City booster box"},
    {"id": "riftbound_radiance", "query": "Riftbound Radiance"},
    {"id": "one_piece_op18",     "query": "One Piece OP-18"},
]

def run():
    init_db()
    results = []
    for item in WATCHLIST:
        try:
            snap = fetch_sold(item["query"], count=100, condition="new")
            if snap:
                snap["product_id"] = item["id"]
                results.append(snap)
                print(f"[eBay] {item['id']}: {snap['sold_count_30d']} ventes/30j | "
                      f"median {snap['sold_price_median']} {snap['currency']} | "
                      f"min {snap['lowest_ask']} | "
                      f"avg {snap['sold_price_avg']}",
                      flush=True)
            else:
                print(f"[eBay] {item['id']}: aucun resultat exploitable", flush=True)
        except Exception as e:
            print(f"[eBay] {item['id']} ERROR: {e}", flush=True)

    if results:
        insert_snapshots([_flatten(r) for r in results])
        print(f"\n{len(results)} snapshots inseres dans storage.db", flush=True)
    else:
        print("\nAucun snapshot recupere.", flush=True)

def _flatten(s):
    return (s["product_id"], s["source"], s["captured_at"],
            s["sold_price_avg"], s["sold_price_median"],
            s["sold_count_30d"], s["active_listings"],
            s["sell_through"], s["lowest_ask"],
            s["currency"], s["raw_json"])

if __name__ == "__main__":
    run()