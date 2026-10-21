"""Contrat d'integration d'un futur agent IA (AI-001 : aucun agent actif).

Separation des responsabilites :
- EDGE fournit le CONTEXTE : sujet, sources deja collectees, datasets
  (valeurs mesurees par les collecteurs), decision du moteur EDGE.
- L'agent fournit du TEXTE STRUCTURE : affirmations, hypotheses,
  incertitudes, limites, avis analytique, demandes de graphiques par
  identifiant de dataset.
- L'agent ne fournit JAMAIS : chiffres de series, prix, montants,
  allocations, decision EDGE. Toute tentative est rejetee a l'ingestion.
- Toute affirmation de l'agent entre en 'unverified' (ou 'simulated') ;
  seul un humain ou un collecteur pourra la passer a 'verified' dans une
  version ulterieure.
- Un fournisseur payant (provider.paid = True) ne peut etre invoque que via
  PaidGate + SpendGuard (verrou R4.2 : reservation, tentative, resultat).
"""
import copy

from intelligence import SCHEMA_ID, SCHEMA_VERSION
from intelligence.validator import assess
from investigation.spend import PaidGate, SpendNotAuthorized

AGENT_ALLOWED_KEYS = {"claims", "agent_opinion", "chart_requests", "notes"}
AGENT_CLAIM_KEYS = {"claim_id", "kind", "statement", "source_ids", "confidence",
                    "contradicting_source_ids", "invalidated_by", "invalidation_reason"}


class AgentOutputRejected(ValueError):
    pass


class AgentNotConfigured(RuntimeError):
    pass


class NullAgentProvider:
    """Fournisseur par defaut : aucun modele branche. Ne fait aucun appel."""
    name = "null_agent"
    paid = False

    def generate(self, agent_input):
        raise AgentNotConfigured("aucun agent IA configure (AI-001)")


def _has_number(o):
    if isinstance(o, bool):
        return False
    if isinstance(o, (int, float)):
        return True
    if isinstance(o, dict):
        return any(_has_number(v) for v in o.values())
    if isinstance(o, list):
        return any(_has_number(v) for v in o)
    return False


def build_agent_input(context):
    """Ce que l'agent recoit : lecture seule, sans donnee privee ni montant
    d'allocation (le contexte EDGE est deja public par construction)."""
    return {"report_id": context["report_id"], "subject": copy.deepcopy(context["subject"]),
            "sources": copy.deepcopy(context["sources"]),
            "datasets": [{k: d[k] for k in ("dataset_id", "title", "unit", "currency", "measure",
                                            "territory", "period", "simulated")} for d in context["datasets"]],
            "edge_decision": copy.deepcopy(context["edge_decision"]),
            "instructions": "Ne produire ni chiffre, ni prix, ni montant, ni decision : seulement des "
                            "affirmations sourcees par source_id, hypotheses, incertitudes, limites et un avis."}


def ingest_agent_output(output, context, created_at, report_version=1, claim_basis=None, computations=None):
    """Transforme la sortie d'un agent en rapport BROUILLON valide.
    Leve AgentOutputRejected si la sortie viole le contrat."""
    if not isinstance(output, dict):
        raise AgentOutputRejected("sortie non structuree")
    extra = set(output) - AGENT_ALLOWED_KEYS
    if extra:
        raise AgentOutputRejected(f"champs interdits pour un agent : {sorted(extra)}")
    claims = []
    known_sources = {s["source_id"]: s for s in context["sources"]}
    for c in output.get("claims", []):
        bad = set(c) - AGENT_CLAIM_KEYS
        if bad:
            raise AgentOutputRejected(f"affirmation {c.get('claim_id')} : champs interdits {sorted(bad)}")
        if _has_number(c):
            raise AgentOutputRejected(f"affirmation {c.get('claim_id')} : valeur numerique structuree interdite")
        for sid in c.get("source_ids", []):
            if sid not in known_sources:
                raise AgentOutputRejected(f"affirmation {c.get('claim_id')} : source inventee {sid!r}")
        cited = [known_sources[s] for s in c.get("source_ids", [])]
        simulated = any(s["simulated"] for s in cited)
        claims.append({**c, "author": "agent",
                       # jamais 'verified' a l'ingestion : verification humaine ou collecteur requise
                       "verification": "simulated" if simulated else "unverified",
                       "source_ids": list(c.get("source_ids", []))})
    op = output.get("agent_opinion")
    if op is not None:
        if _has_number(op) or set(op) - {"stance", "rationale", "claim_ids"}:
            raise AgentOutputRejected("avis de l'agent : seuls stance, rationale, claim_ids sont permis")
        op = {**op, "is_decision": False}
    ds_ids = {d["dataset_id"] for d in context["datasets"]}
    charts = []
    for i, req in enumerate(output.get("chart_requests", [])):
        if _has_number({k: v for k, v in req.items()}) or set(req) - {"type", "title", "dataset_ids"}:
            raise AgentOutputRejected("graphique : seuls type, title, dataset_ids (aucune valeur)")
        unknown = set(req.get("dataset_ids", [])) - ds_ids
        if unknown:
            raise AgentOutputRejected(f"graphique : datasets inconnus {sorted(unknown)}")
        charts.append({"chart_id": f"cht_agent{i + 1}", **req})
    simulated = (any(s["simulated"] for s in context["sources"]) or any(d["simulated"] for d in context["datasets"])
                 or any(c["verification"] == "simulated" for c in claims))
    report = {
        "schema": SCHEMA_ID, "schema_version": SCHEMA_VERSION,
        "report_id": context["report_id"], "report_version": report_version, "supersedes": None,
        "created_at": created_at, "data_as_of": context["data_as_of"],
        "production_status": "draft", "simulated": simulated,
        "subject": copy.deepcopy(context["subject"]),
        "sources": copy.deepcopy(context["sources"]), "claims": claims,
        "datasets": copy.deepcopy(context["datasets"]),  # valeurs EDGE, jamais de l'agent
        "charts": charts, "economics": copy.deepcopy(context["economics"]),
        "decisions": {"agent_opinion": op, "edge_decision": copy.deepcopy(context["edge_decision"])},
        "history": {"previous_versions": [], "related_report_ids": [], "changes": [],
                    "corrections": [], "conclusion_changes": []},
    }
    # (AI-002B) fondements d'interpretation et calculs EDGE, fournis par EDGE
    for c in report["claims"]:
        if claim_basis and c["claim_id"] in claim_basis:
            c["basis"] = copy.deepcopy(claim_basis[c["claim_id"]])
    if computations:
        report["computations"] = copy.deepcopy(computations)
    a = assess(report)
    if not a["valid"]:
        raise AgentOutputRejected("rapport resultant invalide : " + "; ".join(a["errors"][:5]))
    return report


PAID_CONTRACT = "edge.paid_provider.v1"


class PartialResponse(RuntimeError):
    """Reponse facturee mais incomplete ou non structuree : enregistree,
    debitee, jamais ingeree, jamais relancee automatiquement."""


class BillableTransport:
    """SEUL acces reseau confie a un fournisseur payant (contrat v1).

    Chaque request() = une operation facturable = une reservation R4.2
    (reserved -> attempt -> result). Plafond d'operations par execution ;
    transport ferme a la fin : il ne peut pas etre reutilise ensuite.
    """

    def __init__(self, name, guard, query, send, max_operations):
        self.name, self.guard, self.query, self._send = name, guard, query, send
        self.max_operations = max_operations
        self.operations = 0
        self.closed = False

    def request(self, payload):
        if self.closed:
            raise SpendNotAuthorized("transport ferme : aucune operation hors execution autorisee")
        if self.operations >= self.max_operations:
            raise SpendNotAuthorized(f"plafond d'operations facturables atteint ({self.max_operations})")
        res_id = self.guard.reserve(self.name, self.query)  # leve si non autorise
        self.operations += 1
        with self.guard.active(res_id):
            self.guard.consume(self.name, self.query)
            try:
                resp = self._send(payload)
            except BaseException as e:
                self.guard.record_result(res_id, "error", error_type=type(e).__name__)
                raise
        # (AI-002B) identifiants d'operation et couts connus du fournisseur,
        # limites a des champs primitifs listes (jamais de contenu ni de secret)
        billing = {}
        if isinstance(resp, dict) and isinstance(resp.get("billing"), dict):
            billing = {k: v for k, v in resp["billing"].items()
                       if k in ("provider_operation_id", "input_tokens", "output_tokens")
                       and isinstance(v, (str, int)) and not isinstance(v, bool)}
        if not isinstance(resp, dict) or "_partial" in resp:
            reason = resp.get("_partial") if isinstance(resp, dict) else type(resp).__name__
            self.guard.record_result(res_id, "partial", reason=str(reason)[:200], **billing)
            raise PartialResponse(f"reponse incomplete ou non conforme : {reason}")
        self.guard.record_result(res_id, "ok", **billing)
        return resp

    def close(self):
        self.closed = True


def run_agent(provider, agent_input, spend_guard=None, send=None, max_operations=1, max_attempts=1):
    """Seul point d'appel d'un agent.

    Fournisseur gratuit : appel direct. Fournisseur payant : contrat
    edge.paid_provider.v1 obligatoire -> generate(agent_input, transport),
    ou `transport` (BillableTransport) est son unique acces facturable.
    - une reservation par operation externe facturable ;
    - aucune operation au-dela de `max_operations` par tentative ;
    - aucune relance implicite : `max_attempts` (defaut 1) est explicite et
      chaque relance reserve de nouveau ;
    - reponse partielle : enregistree comme telle, debitee, levee, jamais relancee ;
    - sans garde autorise : aucune requete n'est emise.
    Limite : Python ne peut pas empecher un fournisseur d'ouvrir sa propre
    connexion ; le contrat l'interdit et les tests hors ligne le detectent.
    """
    if not getattr(provider, "paid", False):
        return provider.generate(agent_input)
    if spend_guard is None:
        raise SpendNotAuthorized("agent payant sans garde de depense : refuse")
    if getattr(provider, "contract", None) != PAID_CONTRACT:
        raise SpendNotAuthorized("fournisseur payant opaque (contrat edge.paid_provider.v1 absent) : refuse, "
                                 "ses operations facturables ne seraient pas comptees")
    if not callable(send):
        raise SpendNotAuthorized("aucun canal d'envoi fourni par EDGE : refuse")
    # Controle prealable : sans autorisation ni requete approuvee, le
    # fournisseur n'est meme pas invoque (aucun travail, aucune requete).
    if spend_guard.policy is None:
        raise SpendNotAuthorized(spend_guard.reason)
    if agent_input["report_id"] not in spend_guard.allowed:
        raise SpendNotAuthorized(f"requete non approuvee : {agent_input['report_id']!r}")
    for n in (max_operations, max_attempts):
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            raise ValueError("max_operations et max_attempts : entiers >= 1")
    last_error = None
    for _attempt in range(max_attempts):
        transport = BillableTransport(provider.name, spend_guard, agent_input["report_id"], send, max_operations)
        try:
            return provider.generate(agent_input, transport)
        except (SpendNotAuthorized, PartialResponse):
            raise  # jamais relance : refus de depense ou reponse facturee incomplete
        except Exception as e:
            last_error = e
        finally:
            transport.close()
    raise last_error
