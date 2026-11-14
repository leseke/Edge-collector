"""Detection d'indices sur les candidats groupes par produit.

Produit des RAISONS d'investiguer, avec references aux observations.
Ce ne sont pas des decisions d'achat.
"""
from datetime import date

from discovery.engine import BUYABLE_EVIDENCE, SALE_EVIDENCE


def quantile(values, q):
    """Quantile par interpolation lineaire (deterministe)."""
    v = sorted(values)
    if not v:
        return None
    if len(v) == 1:
        return v[0]
    pos = (len(v) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def group_by_product(candidates):
    groups = {}
    for c in candidates:
        groups.setdefault(c["product_key"], []).append(c)
    return groups


def analyze_group(product_key, items, watchlist_keys=(), policy=None, as_of=None):
    policy = policy or {}
    as_of = as_of or date.today()
    min_discount = policy.get("anomaly_min_discount", 0.25)
    min_sold = policy.get("anomaly_min_sold", 3)
    buyable = [c for c in items if c["evidence_type"] in BUYABLE_EVIDENCE]
    sold = [c for c in items if c["evidence_type"] in SALE_EVIDENCE]
    sold_prices = [c["price_eur"] for c in sold]
    sold_median = quantile(sold_prices, 0.5)
    reasons, risks = [], []

    best = None
    for c in buyable:
        total = c["price_eur"] + (c.get("shipping_eur") or 0)
        if best is None or total < best["total_eur"]:
            best = {"id": c["id"], "price_eur": c["price_eur"], "total_eur": round(total, 2),
                    "shipping_known": c.get("shipping_eur") is not None,
                    "source": c["source"], "url": c["source_url"],
                    "evidence_type": c["evidence_type"], "seller_type": c.get("seller_type")}

    if best and sold_median and len(sold) >= min_sold:
        discount = 1 - best["total_eur"] / sold_median
        if discount >= min_discount:
            reasons.append({
                "type": "PRICE_ANOMALY",
                "detail": f"offre {best['total_eur']:.2f} EUR vs mediane de {len(sold)} ventes conclues {sold_median:.2f} EUR (-{discount:.0%})",
                "evidence": [best["id"]] + [c["id"] for c in sold[:10]],
            })
            sold_sources = {c["source"] for c in sold}
            if best["source"] not in sold_sources:
                reasons.append({"type": "CROSS_PLATFORM_SPREAD",
                                "detail": f"achat sur {best['source']}, ventes sur {', '.join(sorted(sold_sources))}",
                                "evidence": [best["id"]]})
    elif best and len(sold) < min_sold:
        # Pas assez de ventes individuelles : on tente les preuves de rang
        # inferieur, chacune etiquetee comme telle.
        from investigation.aggregate import assess, latest_aggregate, DEFAULT_POLICY
        agg = latest_aggregate(items)
        trends = [c for c in items if c["evidence_type"] == "MARKET_TREND"]
        if agg:
            pol = dict(DEFAULT_POLICY, **(policy.get("aggregate_policy") or {}))
            ref = agg["aggregate"]["qty_avg_price_eur"]
            disc = 1 - best["total_eur"] / ref
            if assess(agg, as_of, pol, product_key)["qualifies_screening"] and disc >= min_discount:
                reasons.append({
                    "type": "PRICE_ANOMALY_VS_AGGREGATE",
                    "detail": (f"offre {best['total_eur']:.2f} EUR vs moyenne ponderee "
                               f"{ref:.2f} EUR sur {agg['aggregate']['total_quantity']} unites vendues "
                               f"en {agg['aggregate']['period_days']} j (-{disc:.0%}) [statistique agregee]"),
                    "evidence": [best["id"], agg["id"]]})
        elif trends:
            ref = quantile([c["price_eur"] for c in trends], 0.5)
            disc = 1 - best["total_eur"] / ref
            if disc >= min_discount:
                reasons.append({
                    "type": "BELOW_MARKET_TREND",
                    "detail": f"offre {best['total_eur']:.2f} EUR vs prix de marche indicatif {ref:.2f} EUR (-{disc:.0%}) [pas une vente]",
                    "evidence": [best["id"]] + [c["id"] for c in trends[:5]]})
            risks.append("valorisation uniquement indicative (tendance de marche, aucune vente)")
        else:
            risks.append("aucune vente conclue observee : prix de revente inconnu")

    for av in (c for c in items if c["evidence_type"] == "AVAILABILITY"):
        a = av["availability"]
        if a.get("date_last") and date.fromisoformat(a["date_last"]) < as_of:
            if best and a.get("retail_price_eur") and best["total_eur"] <= a["retail_price_eur"]:
                reasons.append({"type": "RETIRED_AT_OR_BELOW_RETAIL",
                                "detail": f"produit retire de la vente officielle ({a['region']}, {a['date_last']}) et offre a {best['total_eur']:.2f} EUR <= prix boutique {a['retail_price_eur']:.2f} EUR",
                                "evidence": [best["id"], av["id"]]})

    asks = [c["price_eur"] for c in buyable]
    if best and len(asks) >= 3:
        others = sorted(asks)[1:]
        med_others = quantile(others, 0.5)
        if med_others and best["price_eur"] < 0.5 * med_others:
            risks.append("prix tres inferieur aux autres offres : verifier authenticite, etat, vendeur")
    if best and best["evidence_type"] == "ASKING_PRICE" and best.get("seller_type") != "PRO":
        risks.append("vendeur non professionnel ou inconnu")
    if best and not best["shipping_known"]:
        risks.append("frais de port inconnus")
    if any(c["identity_confidence"] != "HIGH" for c in items):
        risks.append("identification produit incertaine")

    sources = sorted({c["source"] for c in items})
    return {
        "product_key": product_key,
        "names": sorted({c["name"] for c in items})[:3],
        "in_watchlist": product_key in set(watchlist_keys),
        "n_buyable": len(buyable),
        "n_sold": len(sold),
        "n_sold_aggregate": sum(c["aggregate"]["total_quantity"] for c in items
                                if c["evidence_type"] == "SOLD_AGGREGATE"),
        "evidence_types": sorted({c["evidence_type"] for c in items}),
        "sold_median_eur": round(sold_median, 2) if sold_median else None,
        "best_offer": best,
        "sources": sources,
        "reasons": reasons,
        "risks": risks,
        "needs_investigation": bool(reasons),
        "simulated": any(c.get("simulated") for c in items),
        "candidate_ids": [c["id"] for c in items],
    }


def analyze(candidates, watchlist_keys=(), policy=None, as_of=None):
    out = [analyze_group(k, v, watchlist_keys, policy, as_of) for k, v in group_by_product(candidates).items()]
    out.sort(key=lambda g: (not g["needs_investigation"], -len(g["reasons"]), -g["n_sold"], g["product_key"]))
    return out
