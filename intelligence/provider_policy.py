"""Registre declaratif et garde-fou commun pour futurs fournisseurs IA EDGE.

Aucun fournisseur n'est instancie ni contacte ici. Les modeles restent non
configures. Les couts inconnus sont refuses. Toute execution payante future
doit passer par execute_paid_provider(), qui exige SpendGuard + reservation
R4.2, et l'adaptateur doit appeler guard.consume() juste avant le reseau.
"""
from contextlib import contextmanager

from investigation.spend import SpendGuard, SpendNotAuthorized

CONTRACT = "edge.provider_adapter.v1"

# Prix, gratuité et modèles évoluent : aucune hypothèse de gratuité.
PROVIDER_CATALOG = {
    "openai": {"cost_status": "unknown", "paid": True, "remote": True,
               "structured_output": True, "timeout_required": True},
    "anthropic": {"cost_status": "unknown", "paid": True, "remote": True,
                  "structured_output": True, "timeout_required": True},
    "google": {"cost_status": "unknown", "paid": True, "remote": True,
               "structured_output": True, "timeout_required": True},
    "deepseek": {"cost_status": "unknown", "paid": True, "remote": True,
                 "structured_output": True, "timeout_required": True},
}

# Préférences de travail uniquement : aucun modèle, aucune sélection/exécution
# automatique. Une spécialité peut rester sans fournisseur assigné.
ROLE_PREFERENCES = {
    "market_intelligence": ("openai", "anthropic", "deepseek"),
    "supply_distribution": ("google", "openai", "deepseek"),
    "actor_community": ("anthropic", "deepseek", "google"),
    "hype_intelligence": ("deepseek", "anthropic", "openai"),
    "grading_intelligence": ("google", "openai", "anthropic"),
    "grading_arbitrage": ("openai", "google", "deepseek"),
    "restoration_preservation": ("google", "anthropic", "openai"),
    "error_card_intelligence": ("anthropic", "google", "deepseek"),
    "private_demand": ("deepseek", "openai", "anthropic"),
}


class ProviderPolicyError(RuntimeError):
    pass


def provider_metadata(adapter):
    """Valide les métadonnées minimales ; toute valeur inconnue ferme l'accès."""
    provider_id = getattr(adapter, "provider_id", None)
    model_id = getattr(adapter, "model_id", None)
    cost_status = getattr(adapter, "cost_status", None)
    paid = getattr(adapter, "paid", None)
    remote = getattr(adapter, "remote", None)
    timeout_support = getattr(adapter, "timeout_support", None)
    if not isinstance(provider_id, str) or provider_id not in PROVIDER_CATALOG:
        raise ProviderPolicyError("fournisseur inconnu ou non enregistré")
    if not isinstance(model_id, str) or not model_id.strip():
        raise ProviderPolicyError("identifiant de modèle explicite requis")
    if cost_status not in {"known", "unknown"} or not isinstance(paid, bool):
        raise ProviderPolicyError("statut de coût inconnu : exécution refusée")
    if remote is not True or timeout_support is not True:
        raise ProviderPolicyError("adaptateur distant sans délai d'exécution garanti")
    if cost_status != "known":
        raise ProviderPolicyError("coût fournisseur non vérifié : exécution refusée")
    if paid and provider_id not in PROVIDER_CATALOG:
        raise ProviderPolicyError("fournisseur payant non autorisé")
    return {"provider_id": provider_id, "model_id": model_id,
            "cost_status": cost_status, "paid": paid, "remote": remote,
            "timeout_support": timeout_support}


def execute_paid_provider(adapter, request_key, spend_guard, *args, **kwargs):
    """Exécute un adaptateur payant sous réservation SpendGuard R4.2.

    L'adaptateur doit appeler spend_guard.consume(provider_id, request_key)
    immédiatement avant son appel externe. S'il ne consomme pas la réservation,
    celle-ci est libérée et le résultat est rejeté. Aucun retry automatique.
    """
    meta = provider_metadata(adapter)
    if not meta["paid"]:
        raise ProviderPolicyError("cet adaptateur n'est pas un adaptateur payant")
    if not isinstance(spend_guard, SpendGuard):
        raise SpendNotAuthorized("SpendGuard absent ou invalide : appel refusé")
    if not isinstance(request_key, str) or not request_key.strip():
        raise SpendNotAuthorized("clé de requête approuvée requise")
    source = "llm:" + meta["provider_id"]
    reservation_id = spend_guard.reserve(source, request_key)
    try:
        with spend_guard.active(reservation_id):
            result = adapter.execute(*args, **kwargs)
    except BaseException as exc:
        attempted = spend_guard._reservations[reservation_id]["state"] != "reserved"
        if attempted:
            spend_guard.record_result(reservation_id, "error",
                                      error_type=type(exc).__name__)
        else:
            spend_guard.release(reservation_id, "appel externe non tente")
        raise
    attempted = spend_guard._reservations[reservation_id]["state"] != "reserved"
    if not attempted:
        spend_guard.release(reservation_id, "adaptateur sans consume R4.2")
        raise SpendNotAuthorized("adaptateur refuse : consume R4.2 non appele")
    spend_guard.record_result(reservation_id, "ok")
    return result


def provider_assignment(role):
    """Retourne des préférences, jamais un choix opérationnel."""
    return {"role": role, "preferred_providers": list(ROLE_PREFERENCES.get(role, ())),
            "model_id": None, "execution_status": "not_configured"}
