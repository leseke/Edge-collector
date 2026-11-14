"""Qualification des statistiques de ventes agregees (ex. BrickLink 6 mois).

Regle strategique : une vente agregee est une preuve de marche exploitable,
pas automatiquement une preuve suffisante pour acheter. Chaque critere est
explicite, chiffre et trace. Les seuils sont des choix de prudence
configurables (config "aggregate_policy"), pas des constantes du marche.
"""
from datetime import date

DEFAULT_POLICY = {
    # Fraicheur : statistique recuperee il y a au plus N jours.
    "max_fetch_age_days": 7,
    # Liquidite : unites vendues sur la periode, et nombre de lots distincts
    # (evite qu'un seul vendeur de 20 unites fasse la statistique).
    "min_total_quantity": 10,
    "min_lots": 5,
    # Representativite / dispersion : ecart max/min et divergence entre
    # moyenne simple et moyenne ponderee par quantite.
    "max_price_spread_ratio": 3.0,
    "max_avg_divergence": 0.20,
    # Region attendue pour un revendeur en France.
    "expected_regions": ["europe", "eu"],
    # Decote prudente appliquee au scenario prudent (hypothese explicite).
    "prudent_haircut": 0.10,
    # Le seuil de depistage (premier filtre) est plus permissif que celui
    # d'achat, mais exige toujours une periode et des quantites reelles.
    "screen_min_total_quantity": 3,
}


def policy_from(config):
    p = dict(DEFAULT_POLICY)
    p.update((config or {}).get("aggregate_policy", {}))
    return p


def latest_aggregate(observations):
    aggs = [o for o in observations if o.get("evidence_type") == "SOLD_AGGREGATE" and o.get("aggregate")]
    return max(aggs, key=lambda o: o["observed_at"]) if aggs else None


def assess(obs, as_of, policy, product_key=None):
    """Retourne {qualifies_screening, qualifies_buy, checks:[{name, ok, detail}]}."""
    a = obs["aggregate"]
    checks = []

    def chk(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    age = (as_of - date.fromisoformat(obs["observed_at"][:10])).days
    chk("fraicheur", 0 <= age <= policy["max_fetch_age_days"],
        f"statistique recuperee il y a {age} j (max {policy['max_fetch_age_days']})")
    chk("quantite_vendue", a["total_quantity"] >= policy["min_total_quantity"],
        f"{a['total_quantity']} unites vendues sur {a['period_days']} j (min {policy['min_total_quantity']})")
    chk("lots_distincts", a["lots"] >= policy["min_lots"],
        f"{a['lots']} lots (min {policy['min_lots']})")
    spread = a["max_price_eur"] / a["min_price_eur"]
    chk("dispersion", spread <= policy["max_price_spread_ratio"],
        f"max/min = {spread:.2f} (max {policy['max_price_spread_ratio']})")
    div = abs(a["avg_price_eur"] - a["qty_avg_price_eur"]) / a["qty_avg_price_eur"]
    chk("coherence_moyennes", div <= policy["max_avg_divergence"],
        f"ecart moyenne simple / ponderee = {div:.0%} (max {policy['max_avg_divergence']:.0%})")
    chk("etat_neuf", a["condition"] == "NEW", f"etat {a['condition']}")
    exact = obs.get("identity_confidence") == "HIGH" and (product_key is None or obs.get("product_key") == product_key)
    chk("correspondance_exacte", exact, f"cle {obs.get('product_key')} / identification {obs.get('identity_confidence')}")
    chk("region", (a.get("region") or "").lower() in policy["expected_regions"],
        f"region {a.get('region')}")
    screening = (a["total_quantity"] >= policy["screen_min_total_quantity"] and exact
                 and a["condition"] == "NEW")
    return {"qualifies_screening": screening,
            "qualifies_buy": all(c["ok"] for c in checks),
            "failed": [c["name"] for c in checks if not c["ok"]],
            "checks": checks,
            "nature": "STATISTIQUE AGREGEE (pas des ventes individuelles)"}


def reference_prices(obs, policy):
    """Prix de revente de reference derives de l'agregat, sans invention :
    prudent = min(moyennes) x (1 - decote), central = moyenne ponderee,
    favorable = max(moyennes). Jamais min/max bruts (souvent aberrants)."""
    a = obs["aggregate"]
    lo = min(a["avg_price_eur"], a["qty_avg_price_eur"])
    hi = max(a["avg_price_eur"], a["qty_avg_price_eur"])
    h = policy["prudent_haircut"]
    return {
        "prudent": (round(lo * (1 - h), 2), f"min(moyennes) {lo:.2f} EUR moins decote prudente {h:.0%}"),
        "central": (a["qty_avg_price_eur"], "moyenne ponderee par quantite (6 mois)"),
        "favorable": (hi, "max(moyenne simple, moyenne ponderee)"),
    }
