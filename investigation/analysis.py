"""Investigation structuree d'un candidat. Entierement deterministe.

Distingue strictement :
  - offres achetables (ASKING_PRICE / RETAIL_OFFER)
  - ventes conclues (SOLD)
  - indicateurs agreges (MARKET_TREND)
Les scenarios sont conditionnels ; aucun prix futur n'est affirme.
"""
from datetime import date, timedelta

from discovery.signals import quantile
from edge_engine import funding_status
from investigation.fees import economics

HORIZONS = {"FLIP": {"prudent": 90, "central": 60, "favorable": 30},
            # Horizon unique : seule la croissance varie, sinon "favorable"
            # peut valoir moins que "prudent" (defaut detecte par les tests).
            "FUTURE_CLASSIC": {"prudent": 5 * 365, "central": 5 * 365, "favorable": 5 * 365}}


def split_evidence(observations, as_of, window_days=90):
    cutoff = as_of - timedelta(days=window_days)
    def recent(o):
        return date.fromisoformat(o["observed_at"][:10]) >= cutoff
    sold = [o for o in observations if o["evidence_type"] == "SOLD" and recent(o)]
    sold_all = [o for o in observations if o["evidence_type"] == "SOLD"]
    buyable = [o for o in observations if o["evidence_type"] in ("ASKING_PRICE", "RETAIL_OFFER")]
    trend = [o for o in observations if o["evidence_type"] == "MARKET_TREND"]
    return sold, sold_all, buyable, trend


def scenarios_from_aggregate(agg_obs, buy, profile, policy):
    from investigation.aggregate import reference_prices
    if not buy:
        return None
    out = {}
    for k, (sale, basis) in reference_prices(agg_obs, policy).items():
        out[k] = economics(buy["price_eur"], buy.get("shipping_eur"), sale, profile, HORIZONS["FLIP"][k])
        out[k]["basis"] = basis + " [statistique agregee]"
    return out


def liquidity(sold_all, buyable, as_of):
    d30 = sum(1 for o in sold_all if (as_of - date.fromisoformat(o["observed_at"][:10])).days <= 30)
    d90 = sum(1 for o in sold_all if (as_of - date.fromisoformat(o["observed_at"][:10])).days <= 90)
    supply = len(buyable)
    months = round(supply / d30, 1) if d30 else None
    return {"sold_30d": d30, "sold_90d": d90, "active_offers_observed": supply,
            "months_of_supply": months,
            "note": "offres observees dans les sources interrogees, pas le marche entier"}


def price_history(sold_all):
    by_month = {}
    for o in sold_all:
        by_month.setdefault(o["observed_at"][:7], []).append(o["price_eur"])
    return [{"month": m, "n": len(v), "median_eur": round(quantile(v, 0.5), 2)}
            for m, v in sorted(by_month.items())]


def confidence(identity_high, sold, sources, fees_verified, as_of, buy_verified, risks):
    pts, why = 0, []
    if identity_high:
        pts += 1; why.append("+1 identification exacte")
    else:
        why.append("0 identification incertaine")
    if len(sold) >= 10:
        pts += 2; why.append(f"+2 {len(sold)} ventes conclues recentes")
    elif len(sold) >= 5:
        pts += 1; why.append(f"+1 {len(sold)} ventes conclues recentes")
    else:
        why.append(f"0 seulement {len(sold)} ventes conclues recentes")
    if len(sources) >= 2:
        pts += 1; why.append("+1 plusieurs sources")
    if fees_verified:
        pts += 1; why.append("+1 frais verifies")
    else:
        why.append("0 frais non verifies")
    prices = [o["price_eur"] for o in sold]
    if len(prices) >= 3:
        mean = sum(prices) / len(prices)
        cv = (sum((p - mean) ** 2 for p in prices) / len(prices)) ** 0.5 / mean
        if cv < 0.25:
            pts += 1; why.append(f"+1 prix homogenes (CV {cv:.2f})")
        else:
            why.append(f"0 prix disperses (CV {cv:.2f})")
    if buy_verified:
        pts += 1; why.append("+1 offre achetable verifiable (lien https)")
    if any("authenticite" in r for r in risks):
        pts -= 2; why.append("-2 prix suspect")
    level = "HIGH" if pts >= 5 else ("MEDIUM" if pts >= 3 else "LOW")
    return level, pts, why


def scenarios_flip(sold, buy, profile):
    prices = [o["price_eur"] for o in sold]
    if len(prices) < 3 or not buy:
        return None
    q = {"prudent": quantile(prices, 0.25), "central": quantile(prices, 0.5),
         "favorable": quantile(prices, 0.75)}
    out = {}
    for k, sale in q.items():
        out[k] = economics(buy["price_eur"], buy.get("shipping_eur"), sale, profile, HORIZONS["FLIP"][k])
        out[k]["basis"] = f"{'P25' if k == 'prudent' else 'mediane' if k == 'central' else 'P75'} de {len(prices)} ventes conclues (90j)"
    return out


def scenarios_future_classic(sold, buy, profile, comparables):
    """comparables : [{name, annual_growth_pct, source_url}] issus de
    produits historiques comparables. Au moins 3, sinon non calculable."""
    valid = [c for c in comparables or [] if isinstance(c.get("annual_growth_pct"), (int, float))]
    prices = [o["price_eur"] for o in sold]
    if len(valid) < 3 or len(prices) < 3 or not buy:
        return None
    g = [c["annual_growth_pct"] / 100 for c in valid]
    base = quantile(prices, 0.5)
    out = {}
    for k, qq in (("prudent", 0.25), ("central", 0.5), ("favorable", 0.75)):
        days = HORIZONS["FUTURE_CLASSIC"][k]
        sale = base * (1 + quantile(g, qq)) ** (days / 365)
        out[k] = economics(buy["price_eur"], buy.get("shipping_eur"), sale, profile, days)
        out[k]["basis"] = f"mediane actuelle x croissance {'P25' if qq == .25 else 'mediane' if qq == .5 else 'P75'} de {len(valid)} comparables"
    return out


def economic_decision(scen, conf_level, min_roi_pct, has_verified_buy, fees_verified=False,
                      basis="INDIVIDUAL_SALES", indicative_evidence=False):
    """basis : INDIVIDUAL_SALES ou SOLD_AGGREGATE.
    Sans scenario : WATCH si une valorisation indicative existe (tendance,
    agregat non qualifie), sinon NO_DATA. Jamais de decision positive."""
    if scen is None:
        if indicative_evidence:
            return "WATCH", "valorisation seulement indicative ou non qualifiee : aucune decision d'achat possible"
        return "NO_DATA", "aucune preuve de valorisation exploitable"
    p, c = scen["prudent"]["net_roi_pct"], scen["central"]["net_roi_pct"]
    if basis == "SOLD_AGGREGATE":
        # Un agregat peut justifier un BUY, jamais un STRONG_BUY.
        if c >= min_roi_pct and p >= 0 and conf_level in ("HIGH", "MEDIUM") and has_verified_buy:
            return "BUY", f"ROI net central {c}% >= {min_roi_pct}% (statistique agregee qualifiee ; plafond BUY)"
        if c >= min_roi_pct:
            return "WATCH", f"ROI central {c}% attractif mais confiance {conf_level}, offre non verifiee ou prudent negatif ({p}%)"
        return "WAIT", f"ROI net central {c}% < seuil {min_roi_pct}%"
    # STRONG_BUY exige des frais verifies : une marge prudente calculee
    # avec des frais supposes n'est pas une preuve forte.
    if p >= min_roi_pct and conf_level == "HIGH" and has_verified_buy and fees_verified:
        return "STRONG_BUY", f"ROI net prudent {p}% >= {min_roi_pct}% avec confiance elevee"
    if c >= min_roi_pct and p >= 0 and conf_level in ("HIGH", "MEDIUM") and has_verified_buy:
        return "BUY", f"ROI net central {c}% >= {min_roi_pct}% et scenario prudent sans perte"
    if c >= min_roi_pct:
        return "WATCH", f"ROI central {c}% attractif mais confiance {conf_level} ou scenario prudent negatif ({p}%)"
    return "WAIT", f"ROI net central {c}% < seuil {min_roi_pct}%"


def investigate(group, observations, as_of, config, fee_profile, fees_verified,
                strategy="FLIP", comparables=None, catalyst_evals=None):
    """group : sortie de discovery.signals.analyze_group ;
    observations : observations normalisees du produit."""
    policy = config.get("investigation_policy", {})
    min_roi = policy.get("min_net_roi_pct", 20)
    sold, sold_all, buyable, trend = split_evidence(observations, as_of)
    buy = group.get("best_offer")
    has_verified_buy = bool(buy and str(buy.get("url", "")).startswith("https://"))
    level, pts, why = confidence(not any("identification" in r for r in group["risks"]),
                                 sold, group["sources"], fees_verified, as_of,
                                 has_verified_buy, group["risks"])
    from investigation.aggregate import assess, latest_aggregate, policy_from
    agg_policy = policy_from(config)
    agg = latest_aggregate(observations)
    agg_assessment = assess(agg, as_of, agg_policy, group["product_key"]) if agg else None
    basis = "INDIVIDUAL_SALES"
    if strategy == "FUTURE_CLASSIC":
        scen = scenarios_future_classic(sold, buy, fee_profile, comparables)
    else:
        scen = scenarios_flip(sold, buy, fee_profile)
        if scen is None and agg_assessment and agg_assessment["qualifies_buy"]:
            scen = scenarios_from_aggregate(agg, buy, fee_profile, agg_policy)
            basis = "SOLD_AGGREGATE"
            a = agg["aggregate"]
            # la confiance tient compte de la nature agregee de la preuve
            pts_agg = 2 if a["total_quantity"] >= 2 * agg_policy["min_total_quantity"] else 1
            pts += pts_agg
            why.append(f"+{pts_agg} statistique agregee qualifiee ({a['total_quantity']} unites, {a['lots']} lots, {a['period_days']} j)")
            level = "HIGH" if pts >= 5 else ("MEDIUM" if pts >= 3 else "LOW")
    indicative = bool(trend) or bool(agg)
    decision, rationale = economic_decision(scen, level, min_roi, has_verified_buy, fees_verified,
                                            basis=basis, indicative_evidence=indicative)
    funding = funding_status(decision, strategy, buy["total_eur"] if buy else None,
                             config, offer_verified=has_verified_buy)
    return {
        "product_key": group["product_key"], "strategy": strategy,
        "sold": sold, "sold_all": sold_all, "buyable": buyable, "trend": trend,
        "best_offer": buy, "liquidity": liquidity(sold_all, buyable, as_of),
        "history": price_history(sold_all), "scenarios": scen,
        "confidence": {"level": level, "points": pts, "why": why},
        "decision": decision, "rationale": rationale,
        "opportunity_alert": decision in ("BUY", "STRONG_BUY"),
        "funding": funding, "min_net_roi_pct": min_roi,
        "catalysts": catalyst_evals or [], "comparables": comparables or [],
        "risks": group["risks"], "reasons": group["reasons"],
        "valuation_basis": basis if scen else None,
        "aggregate_assessment": agg_assessment,
        "simulated": group.get("simulated", False),
    }
