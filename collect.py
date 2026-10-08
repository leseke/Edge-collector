import os
from connectors.ebay import fetch_sold
from storage import init_db, insert_snapshots

# Chaque produit a :
# - query  : mots-cles envoyes a eBay
# - must_all : tous ces mots doivent etre dans le titre
# - must_any : au moins un de ces mots doit etre dans le titre
WATCHLIST = [
    {
        "id": "lego_77073",
        "query": "LEGO 77073",
        "must_all": ["77073"],
        "must_any": ["lego", "fortnite", "battle bus"],
    },
    {
        "id": "lego_75639",
        "query": "LEGO 75639",
        "must_all": ["75639"],
        "must_any": ["lego", "one piece", "going merry"],
    },
    {
        "id": "lego_21371",
        "query": "LEGO 21371",
        "must_all": ["21371"],
        "must_any": ["lego", "wallace", "gromit"],
    },
    {
        "id": "lorcana_hyperia",
        "query": "Lorcana Hyperia City",
        "must_all": ["hyperia"],
        "must_any": ["lorcana", "booster", "box", "coco"],
    },
    {
        "id": "riftbound_radiance",
        "query": "Riftbound Radiance",
        "must_all": ["radiance"],
        "must_any": ["riftbound", "booster", "box"],
    },
    {
        "id": "one_piece_op18",
        "query": "One Piece OP-18",
        "must_all": ["op-18"],
        "must_any": ["one piece", "booster", "box"],
    },
]


def run():
    init_db()
    results = []
    for item in WATCHLIST:
        try:
            snap = fetch_sold(
                item["query"],
                must_all=item.get("must_all"),
                must_any=item.get("must_any"),
                count=100,
            )
            if snap:
                snap["product_id"] = item["id"]
                results.append(snap)
                cv = snap.get("_cv", 0)
                warn = " ⚠️ dispense" if cv > 0.5 else ""
                print(
                    f"[eBay] {item['id']}: "
                    f"{snap['sold_count_30d']} ventes/30j | "
                    f"median {snap['sold_price_median']} {snap['currency']} | "
                    f"min {snap['lowest_ask']} | "
                    f"avg_trunc {snap['sold_price_avg']} | "
                    f"n={snap.get('_n_filtered')} "
                    f"CV={cv}{warn}",
                    flush=True
                )
            else:
                print(f"[eBay] {item['id']}: aucun resultat apres filtres",
                      flush=True)
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