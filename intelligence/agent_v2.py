"""Contrat de sortie edge.agent_output.v2 (modeles de langage).

Separation formelle :
- facts           : REFERENCES a des extraits autorises (extract_id). Le texte
                    est recopie par EDGE : le modele ne peut ni le retaper ni
                    l'alterer.
- computations    : DEMANDES de calcul (methode, dataset, fenetre). EDGE calcule ;
                    un resultat annonce par le modele different est rejete.
- interpretations : texte du modele, toujours non verifie, avec fondement
                    obligatoire (faits et/ou calculs) ; ses nombres doivent
                    provenir de ces faits ou des resultats EDGE.
- hypotheses, uncertainties, limitations : sans aucun chiffre.
- charts          : identifiants de datasets ; opinion : jamais une decision.
Schemas stricts (compatibles Structured Outputs) : tout champ non prevu est refuse.
"""
import re

from intelligence.compliance import numbers, suspicious, tagged_numbers
from intelligence.computations import TOLERANCE, ComputationError, compute, representations
from intelligence.validator import check_schema

CONTRACT = "edge.agent_output.v2"
_ID = r"^{p}[a-z0-9][a-z0-9_.-]{{1,63}}$"


def _str(maxlen=600):
    return {"type": "string", "maxLength": maxlen}


def plan_schema(topic_ids):
    return {"type": "object", "additionalProperties": False, "required": ["topic_ids", "notes"],
            "properties": {"topic_ids": {"type": "array", "items": {"type": "string", "enum": sorted(topic_ids)}},
                           "notes": _str(400)}}


def analysis_schema():
    conf = {"type": "string", "enum": ["low", "medium", "high"]}
    text_items = lambda: {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                                     "required": ["claim_id", "statement", "confidence"],
                                                     "properties": {"claim_id": {"type": "string", "pattern": _ID.format(p="clm_")},
                                                                    "statement": _str(), "confidence": conf}}}
    return {"type": "object", "additionalProperties": False,
            "required": ["facts", "computations", "interpretations", "hypotheses", "uncertainties",
                         "limitations", "charts", "opinion", "insufficient_evidence"],
            "properties": {
                "facts": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                          "required": ["claim_id", "extract_id", "confidence"],
                          "properties": {"claim_id": {"type": "string", "pattern": _ID.format(p="clm_")},
                                         "extract_id": {"type": "string"}, "confidence": conf}}},
                "computations": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                 "required": ["computation_id", "method", "dataset_id", "t_from", "t_to", "claimed_result"],
                                 "properties": {"computation_id": {"type": "string", "pattern": _ID.format(p="cmp_")},
                                                "method": {"type": "string", "enum": ["pct_change", "difference", "mean", "min", "max"]},
                                                "dataset_id": {"type": "string"},
                                                "t_from": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
                                                "t_to": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
                                                "claimed_result": {"type": ["number", "null"]}}}},
                "interpretations": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                    "required": ["claim_id", "statement", "basis_fact_ids", "basis_computation_ids", "confidence"],
                                    "properties": {"claim_id": {"type": "string", "pattern": _ID.format(p="clm_")},
                                                   "statement": _str(), "confidence": conf,
                                                   "basis_fact_ids": {"type": "array", "items": {"type": "string"}},
                                                   "basis_computation_ids": {"type": "array", "items": {"type": "string"}}}}},
                "hypotheses": text_items(), "uncertainties": text_items(), "limitations": text_items(),
                "charts": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                           "required": ["title", "dataset_ids", "type"],
                           "properties": {"title": _str(200), "type": {"type": "string", "enum": ["line", "bar"]},
                                          "dataset_ids": {"type": "array", "items": {"type": "string"}}}}},
                "opinion": {"type": "object", "additionalProperties": False, "required": ["stance", "rationale"],
                            "properties": {"stance": {"type": "string", "enum": ["bullish", "bearish", "neutral", "insufficient_evidence"]},
                                           "rationale": _str()}},
                "insufficient_evidence": {"type": "boolean"}}}


def validate_shape(obj, schema, label):
    return [f"{label} : {e}" for e in check_schema(obj, schema)]


def convert(analysis, inventory, assertion_positions):
    """Sortie v2 -> (sortie v1 pour l'ingestion AI-001, bases, calculs EDGE,
    nombres autorises par affirmation, violations)."""
    V, claims, bases, comps, allowed = [], [], {}, [], {}
    ext = inventory["extracts"]
    ids = set()

    def new_id(cid):
        if cid in ids:
            V.append(f"identifiant duplique {cid}")
        ids.add(cid)

    fact_by_id = {}
    for f in analysis["facts"]:
        new_id(f["claim_id"])
        e = ext.get(f["extract_id"])
        if e is None:
            V.append(f"{f['claim_id']} : extrait inconnu ou non autorise {f['extract_id']!r}")
            continue
        others = sorted({s for pos, srcs in assertion_positions.get(e["assertion_key"], {}).items()
                         if pos != e["position"] for s in srcs})
        c = {"claim_id": f["claim_id"], "kind": "fact", "statement": e["statement"],  # texte recopie par EDGE
             "source_ids": [e["source_id"]], "confidence": f["confidence"]}
        if others:
            c["contradicting_source_ids"] = others
        claims.append(c)
        fact_by_id[f["claim_id"]] = c
    comp_by_id = {}
    for cm in analysis["computations"]:
        if cm["computation_id"] in comp_by_id:
            V.append(f"calcul duplique {cm['computation_id']}")
        d = inventory["datasets"].get(cm["dataset_id"])
        if d is None:
            V.append(f"{cm['computation_id']} : dataset inconnu ou non autorise")
            continue
        try:
            res = compute(cm["method"], d, cm["t_from"], cm["t_to"])
        except (ComputationError, ValueError) as e:
            V.append(f"{cm['computation_id']} : calcul impossible ({e})")
            continue
        claimed = cm["claimed_result"]
        if claimed is not None and abs(claimed - res["result"]) > TOLERANCE:
            V.append(f"{cm['computation_id']} : calcul errone (annonce {claimed}, EDGE {round(res['result'], 2)})")
            continue
        out = {"computation_id": cm["computation_id"], "method": cm["method"], "dataset_id": cm["dataset_id"],
               "t_from": cm["t_from"], "t_to": cm["t_to"], **res, "computed_by": "edge_engine"}
        comps.append(out)
        comp_by_id[cm["computation_id"]] = out
    for it in analysis["interpretations"]:
        new_id(it["claim_id"])
        fb, cb = it["basis_fact_ids"], it["basis_computation_ids"]
        if not fb and not cb:
            V.append(f"{it['claim_id']} : interpretation sans preuve (aucun fait ni calcul de fondement)")
            continue
        miss = [i for i in fb if i not in fact_by_id] + [i for i in cb if i not in comp_by_id]
        if miss:
            V.append(f"{it['claim_id']} : fondement inconnu {miss}")
            continue
        # Nombres admis : ceux des faits cites (avec leur etiquette %), et les
        # RESULTATS des calculs EDGE cites (etiquetes % pour une variation en %).
        # Les valeurs d'entree ne sont pas admises : "hausse de 420 %" a partir
        # d'un prix de 420 est refuse.
        ok_nums = set().union(*(tagged_numbers(fact_by_id[i]["statement"]) for i in fb)) if fb else set()
        for i in cb:
            cm = comp_by_id[i]
            reps = representations(cm["result"])
            ok_nums |= {r + "%" for r in reps} if cm["unit"] == "percent" else reps
        extra = tagged_numbers(it["statement"]) - ok_nums
        if extra:
            V.append(f"{it['claim_id']} : chiffre non justifie par ses faits ou calculs {sorted(extra)}")
            continue
        srcs = sorted({s for i in fb for s in fact_by_id[i]["source_ids"]} |
                      {s for i in cb for s in inventory["datasets"][comp_by_id[i]["dataset_id"]]["provenance"]["source_ids"]})
        claims.append({"claim_id": it["claim_id"], "kind": "interpretation", "statement": it["statement"],
                       "source_ids": srcs, "confidence": it["confidence"]})
        bases[it["claim_id"]] = {"fact_claim_ids": list(fb), "computation_ids": list(cb)}
        allowed[it["claim_id"]] = ok_nums
    for key, kind in (("hypotheses", "hypothesis"), ("uncertainties", "uncertainty"), ("limitations", "limitation")):
        for h in analysis[key]:
            new_id(h["claim_id"])
            if numbers(h["statement"]):
                V.append(f"{h['claim_id']} : chiffre interdit dans une {kind}")
            claims.append({"claim_id": h["claim_id"], "kind": kind, "statement": h["statement"],
                           "source_ids": [], "confidence": h["confidence"]})
    op = dict(analysis["opinion"])
    if analysis["insufficient_evidence"] and op["stance"] != "insufficient_evidence":
        V.append("opinion incoherente avec insufficient_evidence")
    used = [c["claim_id"] for c in claims if c["kind"] in ("fact", "interpretation")][:5]
    v1 = {"claims": claims, "chart_requests": [dict(c) for c in analysis["charts"]],
          "agent_opinion": {"stance": op["stance"], "rationale": op["rationale"], "claim_ids": used}}
    return v1, bases, comps, allowed, V
