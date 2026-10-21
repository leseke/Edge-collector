"""Genere les exemples de reference (deterministes). Donnees 100 % FICTIVES.
python -m intelligence.examples.build_examples
"""
import json
import os

from intelligence import SCHEMA_ID, SCHEMA_VERSION
from intelligence.store import next_version
from intelligence.validator import assess

HERE = os.path.dirname(__file__)
FICTIF = "EXEMPLE FICTIF — aucune valeur reelle"


def months(start_year, start_month, n):
    out, y, m = [], start_year, start_month
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}-01")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def series(dates, values, missing_reason="mois non couvert par la source fictive (exemple de donnee manquante)"):
    return [{"t": t, "value": v, "status": "missing", "missing_reason": missing_reason} if v is None
            else {"t": t, "value": v, "status": "simulated"} for t, v in zip(dates, values)]


def build_v1():
    m = months(2025, 10, 12)
    src = lambda i, title, pub, tier: {"source_id": i, "title": f"{title} ({FICTIF})", "publisher": pub,
                                       "url": None, "published_at": "2026-09-30", "accessed_at": "2026-10-15",
                                       "tier": tier, "simulated": True, "notes": FICTIF}
    return {
        "schema": SCHEMA_ID, "schema_version": SCHEMA_VERSION,
        "report_id": "eir_pokemon-cn-sealed-demo", "report_version": 1, "supersedes": None,
        "created_at": "2026-10-19T12:00:00+00:00", "data_as_of": "2026-10-15T00:00:00+00:00",
        "production_status": "partial", "simulated": True,
        "freshness": {"max_data_age_days": 30},
        "subject": {"title": "Produits scelles Pokemon en Chine continentale — EXEMPLE FICTIF",
                    "market": "Pokemon TCG, produits scelles (chinois simplifie)", "category": "tcg",
                    "region": "CN", "language": "zh-Hans", "tags": ["exemple", "fictif", "ai-001"]},
        "sources": [src("src_marketplace-a", "Releve d'annonces d'une place de marche", "Place de marche fictive A", "secondary"),
                    src("src_ventes-b", "Historique de ventes conclues", "Plateforme fictive B", "primary"),
                    src("src_forum-c", "Discussion de collectionneurs", "Forum fictif C", "unverified")],
        "claims": [
            {"claim_id": "clm_prix-affiche-hausse", "kind": "fact", "verification": "simulated", "author": "collector",
             "statement": "Le prix affiche median du display etudie augmente sur la periode (serie fictive ds_prix-affiche).",
             "source_ids": ["src_marketplace-a"], "confidence": "medium"},
            {"claim_id": "clm_ventes-rares", "kind": "fact", "verification": "simulated", "author": "collector",
             "statement": "Les ventes conclues observees sont peu nombreuses (serie fictive ds_volume).",
             "source_ids": ["src_ventes-b"], "confidence": "medium"},
            {"claim_id": "clm_ecart-affiche-vendu", "kind": "fact", "verification": "simulated", "author": "human",
             "statement": "Les prix affiches depassent nettement les prix de vente realises.",
             "source_ids": ["src_marketplace-a"], "contradicting_source_ids": ["src_forum-c"], "confidence": "low"},
            {"claim_id": "clm_hyp-demande", "kind": "hypothesis", "verification": "unverified", "author": "agent",
             "statement": "La hausse des prix affiches pourrait refleter une demande de collectionneurs plutot qu'une rarete reelle.",
             "source_ids": [], "confidence": "low"},
            {"claim_id": "clm_incertitude-change", "kind": "uncertainty", "verification": "unverified", "author": "human",
             "statement": "La conversion CNY/EUR et les frais d'importation ne sont pas modelises.",
             "source_ids": [], "confidence": "medium"},
            {"claim_id": "clm_limite-echantillon", "kind": "limitation", "verification": "unverified", "author": "human",
             "statement": "Une seule place de marche et une seule plateforme de ventes : echantillon non representatif.",
             "source_ids": [], "confidence": "high"},
            {"claim_id": "clm_frais-hypothese", "kind": "hypothesis", "verification": "unverified", "author": "human",
             "statement": "Hypothese de frais de revente et d'expedition non verifiee.",
             "source_ids": [], "confidence": "low"},
        ],
        "datasets": [
            {"dataset_id": "ds_prix-affiche", "title": "Prix affiche median, display (fictif)", "unit": "currency",
             "currency": "CNY", "measure": "asking_price", "territory": "CN",
             "period": {"start": m[0], "end": m[-1]}, "frequency": "monthly",
             "provenance": {"source_ids": ["src_marketplace-a"], "method": "mediane mensuelle d'annonces (fictif)",
                            "collected_by": "collector"}, "simulated": True,
             "points": series(m, [420, 430, 445, 450, None, 470, 480, 495, 505, 520, 530, 545])},
            {"dataset_id": "ds_prix-vendu", "title": "Prix de vente realise median, display (fictif)", "unit": "currency",
             "currency": "CNY", "measure": "sold_price", "territory": "CN",
             "period": {"start": m[0], "end": m[-1]}, "frequency": "monthly",
             "provenance": {"source_ids": ["src_ventes-b"], "method": "mediane mensuelle de ventes conclues (fictif)",
                            "collected_by": "collector"}, "simulated": True,
             "points": series(m, [380, 385, None, 395, 400, 398, 410, None, 415, 420, 425, 430])},
            {"dataset_id": "ds_volume", "title": "Ventes conclues par mois (fictif)", "unit": "count",
             "currency": None, "measure": "volume", "territory": "CN",
             "period": {"start": m[0], "end": m[-1]}, "frequency": "monthly",
             "provenance": {"source_ids": ["src_ventes-b"], "method": "comptage mensuel (fictif)",
                            "collected_by": "collector"}, "simulated": True,
             "points": series(m, [12, 9, None, 14, 11, 10, 8, None, 13, 9, 7, 8])},
        ],
        "charts": [
            {"chart_id": "cht_prix", "type": "line", "title": "Prix affiche vs prix realise (CNY, fictif)",
             "dataset_ids": ["ds_prix-affiche", "ds_prix-vendu"]},
            {"chart_id": "cht_volume", "type": "bar", "title": "Ventes conclues par mois (fictif)",
             "dataset_ids": ["ds_volume"]},
        ],
        "economics": {
            "listed_price_dataset_ids": ["ds_prix-affiche"], "realized_sale_dataset_ids": ["ds_prix-vendu"],
            "availability": {"buyable_verified": False, "evidence_claim_ids": []},
            "fees": {"claim_ids": ["clm_frais-hypothese"], "verified": False},
            "liquidity": {"claim_ids": ["clm_ventes-rares"]},
            "roi_hypotheses": [
                {"scenario": "favorable", "net_roi_pct": 12.0, "assumption_claim_ids": ["clm_hyp-demande", "clm_frais-hypothese"], "is_hypothesis": True},
                {"scenario": "central", "net_roi_pct": -3.0, "assumption_claim_ids": ["clm_frais-hypothese"], "is_hypothesis": True},
                {"scenario": "unfavorable", "net_roi_pct": -18.0, "assumption_claim_ids": ["clm_frais-hypothese", "clm_incertitude-change"], "is_hypothesis": True}],
            "supply_demand_claim_ids": ["clm_prix-affiche-hausse", "clm_ventes-rares", "clm_hyp-demande"]},
        "decisions": {
            "agent_opinion": {"stance": "insufficient_evidence", "is_decision": False,
                              "rationale": "Ecart affiche/realise non confirme, frais non verifies, achetabilite inconnue.",
                              "claim_ids": ["clm_ecart-affiche-vendu", "clm_frais-hypothese", "clm_limite-echantillon"]},
            "edge_decision": {"decision": "NOT_EVALUATED", "decided_by": "none", "rules_applied": [],
                              "evidence_refs": [], "decided_at": None}},
        "history": {"previous_versions": [], "related_report_ids": [], "changes": [],
                    "corrections": [], "conclusion_changes": []},
    }


def build_v2(v1):
    v2 = next_version(
        v1,
        corrections=[{"correction_id": "cor_1", "target": "$.claims[clm_ecart-affiche-vendu]",
                      "description": "Conclusion infirmee : l'ecart n'est pas confirme par les ventes du forum fictif.",
                      "reason": "nouvelle observation contradictoire (fictive)", "corrected_at": "2026-10-20T09:00:00+00:00"}],
        conclusion_changes=[{"from": "ecart affiche/realise important", "to": "ecart non etabli",
                             "reason": "source contradictoire jugee plus representative (exemple fictif)"}],
        created_at="2026-10-20T09:00:00+00:00")
    for c in v2["claims"]:
        if c["claim_id"] == "clm_ecart-affiche-vendu":
            c.update(kind="invalidated", invalidated_by="clm_ecart-non-etabli",
                     invalidation_reason="contredite par une source plus representative (fictif)")
    v2["claims"].append({"claim_id": "clm_ecart-non-etabli", "kind": "fact", "verification": "simulated",
                         "author": "human", "statement": "L'ecart entre prix affiches et realises n'est pas etabli.",
                         "source_ids": ["src_forum-c"], "confidence": "low"})
    return v2


def main():
    v1 = build_v1()
    v2 = build_v2(v1)
    for name, r in (("pokemon_china_fictif.v1.json", v1), ("pokemon_china_fictif.v2.json", v2)):
        a = assess(r)
        assert a["valid"], a["errors"]
        with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
            json.dump(r, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(name, "->", a["verification_level"], "|", a["label"])


if __name__ == "__main__":
    main()
