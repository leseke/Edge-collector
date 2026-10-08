import os
from connectors.ebay import fetch_sold
from storage import init_db, insert_snapshots

# Taux de conversion approximatif USD -> EUR
# A mettre a jour manuellement de temps en temps, ou remplacer par une API FX
USD_TO_EUR = 0.92

# Chaque produit a :
# - query             : mots-cles envoyes a eBay
# - must_all          : tous ces mots doivent etre dans le titre
# - must_any          : au moins un de ces mots doit etre dans le titre
# - target_buy        : prix EUR en-dessous duquel on considere l'achat
# - target_strong_buy : prix EUR en-dessous duquel on considere l'achat fort
WATCHLIST = [
    {
        "id": "lego_77073",
        "query": "LEGO 77073",
        "must_all": ["77073"],
        "must_any": ["lego", "fortnite", "battle bus"],
        "target_buy": 60,
        "target_strong_buy": 50,
    },
    {
        "id": "lego_75639",
        "query": "LEGO 75639",
        "must_all": ["75639"],
        "must_any": ["lego", "one piece", "going merry"],
        "target_buy": 90,
        "target_strong_buy": 80,
    },
    {
        "id": "lego_21371",
        "query": "LEGO 21371",
        "must_all": ["21371"],
        "must_any": ["lego", "wallace", "gromit"],
        "target_buy": 85,
        "target_strong_buy": 70,
    },
]


def evaluate_signal(prix_eur, item):
    """Retourne (niveau, message) selon le prix vs cibles."""
    strong = item.get("target_strong_buy")
    target = item.get("target_buy")
    if strong and prix_eur <= strong:
        return "STRONG_BUY", f"🔥🔥 ACHAT FORT : {prix_eur:.0f} EUR <= {strong} EUR"
    if target and prix_eur <= target:
        return "BUY", f"🔥 ACHAT : {prix_eur:.0f} EUR <= {target} EUR"
    if target:
        ecart = (prix_eur - target) / target * 100
        return "WAIT", f"⏸  ATTENDRE : {prix_eur:.0f} EUR > {target} EUR (+{ecart:.0f}%)"
    return "WATCH", f"👁  WATCH : {prix_eur:.0f} EUR (pas de cible definie)"


def run():
    init_db()
    results = []
    alerts = []

    for item in WATCHLIST:
        try:
            snap = fetch_sold(
                item["query"],
                must_all=item.get("must_all"),
                must_any=item.get("must_any"),
                count=100,
            )
            if not snap:
                print(f"[eBay] {item['id']}: aucun resultat apres filtres",
                      flush=True)
                continue

            snap["product_id"] = item["id"]
            results.append(snap)

            cv = snap.get("_cv", 0)
            warn = " ⚠️ pollue" if cv > 0.5 else ""

            # Affichage donnees brutes
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

            # Conversion et evaluation
            prix_eur = snap["sold_price_median"] * USD_TO_EUR
            niveau, message = evaluate_signal(prix_eur, item)
            print(f"   {message}", flush=True)

            if niveau in ("BUY", "STRONG_BUY"):
                alerts.append({"id": item["id"], "niveau": niveau,
                               "prix_eur": prix_eur, "message": message})

        except Exception as e:
            print(f"[eBay] {item['id']} ERROR: {e}", flush=True)

    if results:
        insert_snapshots([_flatten(r) for r in results])
        print(f"\n{len(results)} snapshots inseres dans storage.db", flush=True)

    # Resume des alertes
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