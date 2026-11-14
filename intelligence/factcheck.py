"""Promotion d'une affirmation en 'verified' (mecanisme prepare, AI-001.1).

Une verification est un ACTE TRACE : qui (humain ou collecteur identifie,
jamais un agent IA), quand, selon quelle procedure, sur quelle preuve
localisee. Elle produit une NOUVELLE VERSION du rapport (l'historique publie
reste immuable). Le validateur controle la coherence de cette trace ; il ne
peut pas en garantir la verite.
"""
import copy

from intelligence.store import next_version
from intelligence.validator import assess

ALLOWED_ROLES = {"human", "collector"}


def promote_claim(report, claim_id, verifier, method, procedure, evidence, at, notes=None):
    if not isinstance(verifier, dict) or verifier.get("role") not in ALLOWED_ROLES or not verifier.get("id"):
        raise ValueError("verificateur humain ou collecteur identifie requis (un agent IA ne verifie pas)")
    claim = next((c for c in report["claims"] if c["claim_id"] == claim_id), None)
    if claim is None:
        raise ValueError(f"affirmation inconnue : {claim_id}")
    if claim["kind"] != "fact":
        raise ValueError("seul un fait peut etre verifie")
    record = {"verified_by": {"role": verifier["role"], "id": verifier["id"]}, "verified_at": at,
              "method": method, "procedure": procedure, "evidence": copy.deepcopy(evidence)}
    if notes:
        record["notes"] = notes
    new = next_version(report, created_at=at, corrections=[{
        "correction_id": f"verif-{claim_id}-v{report['report_version'] + 1}",
        "target": f"$.claims[{claim_id}]",
        "description": f"affirmation verifiee ({method}, procedure {procedure}) par {verifier['role']}:{verifier['id']}",
        "reason": "verification documentee", "corrected_at": at}])
    for c in new["claims"]:
        if c["claim_id"] == claim_id:
            c["verification"] = "verified"
            c["verification_record"] = record
    a = assess(new)
    if not a["valid"]:
        raise ValueError("promotion invalide : " + "; ".join(a["errors"][:5]))
    return new
