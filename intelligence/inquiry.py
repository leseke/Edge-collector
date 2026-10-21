"""Orchestrateur AI-002A : question -> plan -> inventaire -> agent ->
conformite -> ingestion (AI-001.1) -> validation -> stockage -> dossier.

Statuts : REPORT | NO_DATA | AMBIGUOUS | INVALID | REJECTED.
- Aucun reseau, aucune depense : un fournisseur payant passe par run_agent
  (verrou R4.2) et, sans garde, est refuse avant tout appel.
- La decision EDGE vient du contexte EDGE (NOT_EVALUATED ici), jamais de l'agent.
- Un rapport automatique est au mieux 'partial' : jamais complet ni verifie.
- Une nouvelle execution produit une NOUVELLE VERSION ; l'ancienne reste.
"""
import copy
import hashlib
from datetime import datetime, timezone

from intelligence.agent_contract import (AgentOutputRejected, PartialResponse, build_agent_input,
                                         ingest_agent_output, run_agent)
from intelligence.agent_v2 import CONTRACT as V2, analysis_schema, convert, plan_schema, validate_shape
from intelligence.compliance import check_agent_output, suspicious
from intelligence.offline_agent import OfflineAgentProvider
from intelligence.planner import norm, plan_question
from intelligence.store import PublishRefused, next_version
from intelligence.validator import assess, content_sha256, timeliness
from investigation.spend import SpendNotAuthorized

EDGE_DECISION_NOT_EVALUATED = {"decision": "NOT_EVALUATED", "decided_by": "none", "rules_applied": [],
                               "evidence_refs": [], "decided_at": None}
CONTENT_KEYS = ("created_at", "data_as_of", "production_status", "simulated", "subject", "sources", "claims",
                "datasets", "charts", "economics", "decisions", "freshness")


def report_id_for(question, corpus_id):
    from intelligence.store import INQUIRY_PREFIX
    return INQUIRY_PREFIX + hashlib.sha256(f"{corpus_id}|{norm(question).strip()}".encode()).hexdigest()[:16]


def _result(status, **kw):
    return {"status": status, "report": None, "entry": None, "dossier": None, "dossier_path": None,
            "violations": [], **kw}


def run_inquiry(question, corpora, store, now=None, provider=None, spend_guard=None, send=None, max_operations=1):
    now = now or datetime.now(timezone.utc)
    plan = plan_question(question, corpora)
    if plan["status"] != "OK":
        return _result(plan["status"], plan=plan)
    corpus = next(c for c in corpora if c.corpus_id == plan["corpus_id"])

    # --- inventaire : uniquement le corpus autorise, extraits suspects ecartes
    topics = [sq["topic_id"] for sq in plan["subquestions"]]
    excluded, extracts = [], []
    for e in corpus.extracts.values():
        if e["topic_id"] not in topics:
            continue
        if suspicious(e["statement"]):
            excluded.append({"extract_id": e["extract_id"], "source_id": e["source_id"],
                             "reason": "contenu assimilable a une consigne (source tierce) : ecarte, non republie"})
        else:
            extracts.append(e)
    ds_ids = sorted({i for t in topics for i in (d["dataset_id"] for d in corpus.datasets_for(t))})
    datasets = [corpus.datasets[i] for i in ds_ids]
    coverage = {d["dataset_id"]: sum(1 for p in d["points"] if p["value"] is not None) for d in datasets}
    answered = {t: bool([e for e in extracts if e["topic_id"] == t] or
                        [d for d in corpus.datasets_for(t) if coverage.get(d["dataset_id"])]) for t in topics}
    for sq in plan["subquestions"]:
        sq["status"] = "answered" if answered[sq["topic_id"]] else "unanswered"
    if not any(answered.values()):
        return _result("NO_DATA", plan=plan, reason="aucune donnee autorisee pour les sous-questions")
    src_ids = sorted({e["source_id"] for e in extracts} | {s for d in datasets for s in d["provenance"]["source_ids"]})
    sources = [corpus.sources[s] for s in src_ids]
    tl = timeliness({"data_as_of": corpus.data_as_of, "freshness": corpus.freshness}, now)

    # --- contexte EDGE (la decision et les valeurs viennent d'EDGE, pas de l'agent)
    rid = report_id_for(question, corpus.corpus_id)
    economics = {"listed_price_dataset_ids": [d["dataset_id"] for d in datasets if d["measure"] in ("asking_price", "retail_price")],
                 "realized_sale_dataset_ids": [d["dataset_id"] for d in datasets if d["measure"] == "sold_price"],
                 "availability": {"buyable_verified": False, "evidence_claim_ids": []},
                 "fees": {"claim_ids": [], "verified": False}, "liquidity": {"claim_ids": []},
                 "roi_hypotheses": [], "supply_demand_claim_ids": []}
    context = {"report_id": rid, "subject": corpus.subject, "sources": sources, "datasets": datasets,
               "data_as_of": corpus.data_as_of, "economics": economics,
               "edge_decision": copy.deepcopy(EDGE_DECISION_NOT_EVALUATED)}
    agent_input = build_agent_input(context)
    agent_input.update({"question": question, "plan": plan, "simulated": corpus.simulated,
                        "dataset_topics": corpus.dataset_topics, "dataset_coverage": coverage,
                        "timeliness": {"status": tl["status"]}, "excluded_count": len(excluded),
                        "extracts": [{"extract_id": e["extract_id"], "source_id": e["source_id"],
                                      "topic_id": e["topic_id"], "assertion_key": e["assertion_key"],
                                      "position": e["position"], "statement": e["statement"],
                                      "untrusted": True} for e in extracts]})

    # (AI-002B) donnees pour un modele : valeurs autorisees, aucune donnee privee
    agent_input["datasets_for_model"] = [
        {k: d[k] for k in ("dataset_id", "title", "unit", "currency", "measure", "territory", "period", "simulated")}
        | {"points": [{"t": p["t"], "value": p["value"]} for p in d["points"]], "points_with_data": coverage[d["dataset_id"]]}
        for d in datasets]
    agent_input["sources_for_model"] = [{k: s[k] for k in ("source_id", "publisher", "tier", "simulated")} for s in sources]

    # --- agent (gratuit : direct ; payant : activation + verrou R4.2 obligatoires)
    provider = provider or OfflineAgentProvider()
    if getattr(provider, "paid", False) and hasattr(provider, "enabled"):
        ok, why = provider.enabled()
        if not ok:
            return _result("REJECTED", plan=plan, violations=[f"fournisseur refuse avant tout appel : {why}"])
    try:
        output = run_agent(provider, agent_input, spend_guard, send=send, max_operations=max_operations)
    except SpendNotAuthorized as e:
        return _result("REJECTED", plan=plan, violations=[f"depense non autorisee : {e}"])
    except PartialResponse as e:
        return _result("REJECTED", plan=plan, violations=[f"reponse partielle du fournisseur : {e}"])
    except Exception as e:  # erreur HTTP, delai, quota fournisseur : jamais de relance implicite
        return _result("REJECTED", plan=plan, violations=[f"erreur du fournisseur : {type(e).__name__}"])
    inventory = {"sources": {s["source_id"]: s for s in sources},
                 "extracts": {e["extract_id"]: e for e in extracts},
                 "datasets": {d["dataset_id"]: d for d in datasets}}
    bases, comps, allowed, operations = None, None, None, []
    if isinstance(output, dict) and output.get("contract") == V2:
        topics_ok = [sq["topic_id"] for sq in plan["subquestions"]]
        v = validate_shape(output.get("plan"), plan_schema(topics_ok), "plan du modele")
        v += validate_shape(output.get("analysis"), analysis_schema(), "analyse du modele")
        if v:
            return _result("REJECTED", plan=plan, violations=v[:10])
        positions = {}
        for e in extracts:
            positions.setdefault(e["assertion_key"], {}).setdefault(e["position"], []).append(e["source_id"])
        output_v1, bases, comps, allowed, v = convert(output["analysis"], inventory, positions)
        if v:
            return _result("REJECTED", plan=plan, violations=v[:10])
        operations = output.get("operations", [])
        output = output_v1
    violations = check_agent_output(output, inventory, allowed)
    if violations:
        return _result("REJECTED", plan=plan, violations=violations)
    try:
        report = ingest_agent_output(output, context, now.isoformat(), claim_basis=bases, computations=comps)
    except AgentOutputRejected as e:
        return _result("REJECTED", plan=plan, violations=[f"ingestion : {e}"])
    report["production_status"] = "partial"  # jamais complet : affirmations non verifiees
    # (AI-002C) nature de l'affirmation chez la source, reportee par EDGE depuis
    # le corpus (opinion, affirmation commerciale, estimation) : jamais par l'agent
    by_stmt = {(e["statement"], e["source_id"]): e for e in extracts}
    for c in report["claims"]:
        if c["kind"] == "fact":
            e = next((by_stmt[(c["statement"], s)] for s in c["source_ids"] if (c["statement"], s) in by_stmt), None)
            if e is not None and e.get("claim_type"):
                c["source_claim_type"] = e["claim_type"]
    if corpus.freshness:
        report["freshness"] = copy.deepcopy(corpus.freshness)

    # --- versionnement : une nouvelle execution = nouvelle version
    try:
        previous = store.read(rid)
    except KeyError:
        previous = None
    if previous is not None:
        nv = next_version(previous, changes=[{"path": "$", "reason": "nouvelle execution de l'enquete"}])
        for k in CONTENT_KEYS:
            if k in report:
                nv[k] = report[k]
        report = nv
    a = assess(report, now=now)
    if not a["valid"]:
        return _result("REJECTED", plan=plan, violations=a["errors"][:10])

    # --- dossier d'enquete
    contradictions = []
    keys = {}
    for e in extracts:
        keys.setdefault(e["assertion_key"], {}).setdefault(e["position"], []).append(e["source_id"])
    for k, pos in sorted(keys.items()):
        if len(pos) > 1:
            contradictions.append({"assertion_key": k, "positions": {p: sorted(s) for p, s in pos.items()}})
    refresh = [{"type": "data_age", "data_as_of": corpus.data_as_of, "max_age_days": tl["max_age_days"]},
               {"type": "corpus_changed", "corpus_id": corpus.corpus_id, "sha256": corpus.sha256}]
    refresh += [{"type": "unanswered_subquestion", "corpus_id": corpus.corpus_id, "topic_id": sq["topic_id"]}
                for sq in plan["subquestions"] if sq["status"] == "unanswered"]
    dossier = {"schema": "edge.inquiry_dossier.v1", "report_id": rid, "report_version": report["report_version"],
               "report_sha256": content_sha256(report), "question": question, "created_at": now.isoformat(),
               "agent": provider.name, "corpus": {"corpus_id": corpus.corpus_id, "sha256": corpus.sha256,
                                                  "simulated": corpus.simulated},
               "plan": plan,
               "inventory": {"sources": src_ids, "datasets": [{"dataset_id": i, "points_with_data": coverage[i]} for i in ds_ids],
                             "extracts_used": [e["extract_id"] for e in extracts], "excluded_extracts": excluded},
               "contradictions": contradictions,
               "unknowns": [sq["subquestion_id"] for sq in plan["subquestions"] if sq["status"] == "unanswered"],
               "compliance": {"violations": [], "verification_level": a["verification_level"]},
               "timeliness_at_run": tl, "refresh_conditions": refresh,
               "agent_output_contract": V2 if operations else "edge.agent_output.v1",
               # identifiants seulement : jetons et couts restent dans le journal PRIVE
               "agent_operations": [{"provider_operation_id": o.get("provider_operation_id")} for o in operations],
               "agent_costs": "journal prive de depense (private/), jamais publie" if operations else None}
    # Publication conjointe rapport + dossier (deux phases, AI-002B)
    try:
        entry = store.publish(report, dossier)
    except PublishRefused as e:
        return _result("REJECTED", plan=plan, violations=[str(e)])
    return {"status": "REPORT", "report": report, "entry": entry, "dossier": dossier,
            "dossier_path": entry["dossier_path"], "violations": [], "plan": plan}


def refresh_due(dossier, now, corpora):
    """Conditions OBJECTIVES d'actualisation (aucune appreciation)."""
    reasons, by_id = [], {c.corpus_id: c for c in corpora}
    for cond in dossier["refresh_conditions"]:
        if cond["type"] == "data_age":
            t = timeliness({"data_as_of": cond["data_as_of"], "freshness": {"max_data_age_days": cond["max_age_days"]}}, now)
            if t["status"] == "stale":
                reasons.append(f"anciennete des donnees : {t['data_age_days']:.0f} j > {cond['max_age_days']} j")
        elif cond["type"] == "corpus_changed":
            c = by_id.get(cond["corpus_id"])
            if c is None:
                reasons.append(f"corpus {cond['corpus_id']} indisponible")
            elif c.sha256 != cond["sha256"]:
                reasons.append(f"corpus modifie depuis l'enquete ({cond['corpus_id']})")
        elif cond["type"] == "unanswered_subquestion":
            c = by_id.get(cond["corpus_id"])
            t = cond["topic_id"]
            if c and ([e for e in c.extracts_for(t) if not suspicious(e["statement"])] or
                      [d for d in c.datasets_for(t) if any(p["value"] is not None for p in d["points"])]):
                reasons.append(f"sous-question {t} desormais documentee dans le corpus")
    return reasons
