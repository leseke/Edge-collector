"""Rapport d'investigation en 20 sections (JSON + Markdown).

Le rapport complet contient le statut de financement : il est PRIVE.
public_report() en retire le financement pour une eventuelle publication.
"""
from edge_engine import PRIVATE_PRODUCT_KEYS


def _thesis(inv):
    parts = [r["detail"] for r in inv["reasons"]]
    for c in inv["catalysts"]:
        parts.append(f"catalyseur possible ({c['catalyst_id']}, J{c['days_to_event']:+d}) — hypothese a tester")
    return parts or ["aucune asymetrie etayee par les donnees"]


def _counter(inv):
    out = list(inv["risks"])
    if inv.get("valuation_basis") == "SOLD_AGGREGATE":
        out.append("valorisation issue de statistiques agregees (moyennes sur 6 mois), pas de ventes individuelles : "
                   "dispersion intra-periode et tendance recente non observees")
        out.append("prix de reference mesure sur une plateforme (ex. BrickLink Europe) : la revente sur un autre canal "
                   "(eBay FR...) n'est pas garantie au meme prix")
    for c in inv["catalysts"]:
        out.extend(c["competing_explanations"])
    if inv["liquidity"]["months_of_supply"] and inv["liquidity"]["months_of_supply"] > 3:
        out.append(f"offre observee = {inv['liquidity']['months_of_supply']} mois de ventes : revente potentiellement lente")
    return out or ["aucune contre-these specifique identifiee (ce n'est pas une preuve de solidite)"]


def build_report(inv, name, as_of):
    best = inv["best_offer"]
    scen = inv["scenarios"]
    sold_prices = sorted(o["price_eur"] for o in inv["sold"])
    sections = {
        "01_identification": {"product_key": inv["product_key"], "name": name},
        "02_reference_edition_etat_marche": {
            "condition": "NEUF/SCELLE exige (occasion rejetee a la normalisation)",
            "markets": sorted({o.get("source") for o in inv["sold_all"] + inv["buyable"]})},
        "03_prix_observes": {"buyable_prices_eur": sorted(o["price_eur"] for o in inv["buyable"]),
                             "market_trend_eur": [o["price_eur"] for o in inv["trend"]],
                             "note": "un prix d'annonce n'est pas une vente conclue"},
        "04_offres_achetables": best,
        "05_ventes_conclues": {"n_90d": len(sold_prices), "prices_eur": sold_prices,
                               "sources": [o["url"] for o in inv["sold"]][:10],
                               "statistiques_agregees": inv.get("aggregate_assessment"),
                               "base_de_valorisation": inv.get("valuation_basis")},
        "06_liquidite": inv["liquidity"],
        "07_historique_prix": inv["history"],
        "08_comparables": inv["comparables"] or "aucun comparable fourni",
        "09_rarete_reedition": "non evalue automatiquement : verifier statut de production et annonces de reedition",
        "10_catalyseurs": inv["catalysts"],
        "11_pourquoi_mal_valorise": _thesis(inv),
        "12_these": _thesis(inv),
        "13_contre_these": _counter(inv),
        "14_invalidation": ["ventes conclues sous le prix d'achat total pendant 30 jours",
                            "annonce de reedition / reapprovisionnement",
                            "offre disponible qui augmente fortement"]
                           + [t for c in inv["catalysts"] for t in c["invalidation_tests"]],
        "15_scenarios": scen or "non calculable (preuves insuffisantes)",
        "16_rentabilite_nette": {k: {kk: v[kk] for kk in ("buy_total_eur", "net_resale_eur", "fees_eur", "net_profit_eur", "net_roi_pct")}
                                 for k, v in scen.items()} if scen else None,
        "17_rendement_annualise": {k: v["annualized_pct"] for k, v in scen.items()} if scen else None,
        "18_immobilisation": {"holding_days_assumed": {k: v["holding_days"] for k, v in scen.items()} if scen else None,
                              "months_of_supply": inv["liquidity"]["months_of_supply"],
                              "note": "durees de detention = hypotheses de la strategie, pas des mesures"},
        "19_confiance": inv["confidence"],
        "20_conclusion": {"decision_economique": inv["decision"], "justification": inv["rationale"],
                          "opportunity_alert": inv["opportunity_alert"],
                          "seuil_roi_net_pct": inv["min_net_roi_pct"],
                          "financement": inv["funding"],
                          "rappel": "BUY n'est pas un achat automatique ; aucun rendement n'est garanti."},
    }
    return {"schema_version": 1, "as_of": as_of.isoformat(), "strategy": inv["strategy"],
            "simulated": inv["simulated"], "sections": sections}


def public_report(report):
    r = dict(report)
    s = dict(r["sections"])
    concl = {k: v for k, v in s["20_conclusion"].items() if k != "financement"}
    s["20_conclusion"] = concl
    r["sections"] = s
    return r


def to_markdown(report):
    s = report["sections"]
    lines = [f"# Investigation — {s['01_identification']['name']}",
             f"`{s['01_identification']['product_key']}` · stratégie {report['strategy']} · au {report['as_of']}"]
    if report["simulated"]:
        lines.append("\n> **DONNÉES SIMULÉES (fixtures)** — aucune collecte réelle.")
    c = s["20_conclusion"]
    lines += [f"\n**Décision économique : {c['decision_economique']}** — {c['justification']}",
              f"Confiance : {s['19_confiance']['level']} ({s['19_confiance']['points']} pts)"]
    if "financement" in c:
        f = c["financement"]
        lines.append(f"Financement : exécutable = {f['execution_ready']} ; blocages : {', '.join(f['execution_blockers']) or 'aucun'}")
    if s["04_offres_achetables"]:
        b = s["04_offres_achetables"]
        lines.append(f"\nMeilleure offre : {b['total_eur']} € ({b['source']}) {b['url']}")
    v = s["05_ventes_conclues"]
    lines.append(f"Ventes individuelles conclues (90 j) : {v['n_90d']}")
    agg = v.get("statistiques_agregees")
    if agg:
        lines.append(f"\n**Statistique agrégée — {agg['nature']}** : "
                     f"{'qualifiée pour BUY' if agg['qualifies_buy'] else 'NON qualifiée pour BUY'}")
        lines += [f"- {'✅' if c['ok'] else '❌'} {c['name']} : {c['detail']}" for c in agg["checks"]]
    if isinstance(s["15_scenarios"], dict):
        lines.append("\n| Scénario | Revente | Net encaissé | Profit net | ROI net | Annualisé | Base |")
        lines.append("|---|---|---|---|---|---|---|")
        for k, x in s["15_scenarios"].items():
            lines.append(f"| {k} | {x['sale_price_eur']} € | {x['net_resale_eur']} € | {x['net_profit_eur']} € | {x['net_roi_pct']} % | {x['annualized_pct']} % | {x['basis']} |")
        lines.append("\n_Annualisation d'un flip court : indicative, suppose une rotation répétable qui n'est pas démontrée._")
    else:
        lines.append(f"\nScénarios : {s['15_scenarios']}")
    for title, key in (("Thèse", "12_these"), ("Contre-thèse", "13_contre_these"), ("Invalidation", "14_invalidation")):
        lines.append(f"\n**{title}**")
        lines += [f"- {x}" for x in s[key]]
    for cat in s["10_catalyseurs"]:
        lines.append(f"\n**Chaîne catalyseur {cat['catalyst_id']}** ({cat['disclaimer']})")
        lines += [f"- {l['step']} : {l['content']} [{l['status']}]" for l in cat["chain"]]
    lines.append("\n**Confiance — détail**")
    lines += [f"- {w}" for w in s["19_confiance"]["why"]]
    lines.append(f"\n_{c['rappel']}_")
    return "\n".join(lines) + "\n"
