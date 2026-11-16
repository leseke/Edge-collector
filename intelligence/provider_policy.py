"""Registre declaratif et garde-fou commun pour futurs fournisseurs IA EDGE.

Aucun fournisseur n'est instancie ni contacte ici. Les modeles restent non
configures. Les couts inconnus ou non verifies dans le registre public sont
refuses. Toute execution payante exige SpendGuard R4.2 et un cout prudent.
"""
import math

from discovery.access import load_registry
from investigation.spend import SpendGuard, SpendNotAuthorized

CONTRACT = "edge.provider_adapter.v1"

# Catalogue de capacites uniquement. Il ne vaut ni verification contractuelle,
# ni validation des tarifs, ni autorisation d'execution.
PROVIDER_CATALOG = {
    "openai": {"remote": True, "structured_output": True, "timeout_required": True},
    "anthropic": {"remote": True, "structured_output": True, "timeout_required": True},
    "google": {"remote": True, "structured_output": True, "timeout_required": True},
    "deepseek": {"remote": True, "structured_output": True, "timeout_required": True},
}

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


def _positive_finite(value):
    if isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number > 0


def provider_metadata(adapter, registry=None):
    """Valide adaptateur ET registre d'acces/tarifs ; toute inconnue bloque."""
    provider_id = getattr(adapter, "provider_id", None)
    model_id = getattr(adapter, "model_id", None)
    cost_status = getattr(adapter, "cost_status", None)
    paid = getattr(adapter, "paid", None)
    remote = getattr(adapter, "remote", None)
    timeout_support = getattr(adapter, "timeout_support", None)
    if not isinstance(provider_id, str) or provider_id not in PROVIDER_CATALOG:
        raise ProviderPolicyError("fournisseur inconnu ou non enregistre")
    if not isinstance(model_id, str) or not model_id.strip():
        raise ProviderPolicyError("identifiant de modele explicite requis")
    if cost_status != "known" or not isinstance(paid, bool):
        raise ProviderPolicyError("statut de cout inconnu : execution refusee")
    if remote is not True or timeout_support is not True:
        raise ProviderPolicyError("adaptateur distant sans delai d'execution garanti")

    if registry is None:
        registry = load_registry()
    source = registry.get(provider_id) if isinstance(registry, dict) else None
    if not isinstance(source, dict) or source.get("status") != "VERIFIED":
        raise ProviderPolicyError("registre fournisseur non VERIFIED : execution refusee")
    if source.get("paid") is not True or paid is not True:
        raise ProviderPolicyError("statut payant du fournisseur incoherent ou non autorise")
    expected_cost = source.get("estimated_usd_per_call")
    if not _positive_finite(expected_cost):
        raise ProviderPolicyError("cout USD par operation absent ou non verifie dans le registre")
    return {"provider_id": provider_id, "model_id": model_id, "cost_status": cost_status,
            "paid": paid, "remote": remote, "timeout_support": timeout_support,
            "estimated_usd_per_call": float(expected_cost)}


def execute_paid_provider(adapter, request_key, spend_guard, *args, registry=None, **kwargs):
    """Execute un adaptateur payant sous reservation SpendGuard R4.2.

    Le registre doit etre VERIFIED et comporter un cout USD par operation.
    L'estimation privee SpendGuard doit couvrir au moins ce cout. L'adaptateur
    doit appeler consume() juste avant le reseau. Aucun retry automatique.
    """
    meta = provider_metadata(adapter, registry=registry)
    if not meta["paid"]:
        raise ProviderPolicyError("cet adaptateur n'est pas un adaptateur payant")
    if not isinstance(spend_guard, SpendGuard):
        raise SpendNotAuthorized("SpendGuard absent ou invalide : appel refuse")
    if not isinstance(request_key, str) or not request_key.strip():
        raise SpendNotAuthorized("cle de requete approuvee requise")
    if spend_guard.policy is None:
        raise SpendNotAuthorized("politique SpendGuard absente ou invalide")
    if spend_guard.policy["est_usd_per_call"] + 1e-12 < meta["estimated_usd_per_call"]:
        raise SpendNotAuthorized("estimation SpendGuard inferieure au cout fournisseur verifie")
    source = "llm:" + meta["provider_id"]
    reservation_id = spend_guard.reserve(source, request_key)
    try:
        with spend_guard.active(reservation_id):
            result = adapter.execute(*args, **kwargs)
    except BaseException as exc:
        attempted = spend_guard._reservations[reservation_id]["state"] != "reserved"
        if attempted:
            spend_guard.record_result(reservation_id, "error", error_type=type(exc).__name__)
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
    """Retourne des preferences, jamais un choix operationnel."""
    return {"role": role, "preferred_providers": list(ROLE_PREFERENCES.get(role, ())),
            "model_id": None, "execution_status": "not_configured"}
