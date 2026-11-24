"""Subscription-aware provider routing. Decisions only; never executes providers."""
import math

from intelligence.subscription_entitlements import CONTRACT, FREE, PREMIUM


class ProviderRouteDenied(RuntimeError):
    pass


def _finite_nonnegative(value):
    if isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number >= 0


def route_provider(entitlements, provider_id, registry, usage=None,
                   estimated_cost_usd=None, premium_budget_remaining_usd=None):
    """Return a routing decision only; all missing/unknown facts fail closed.

    Free tier: registry VERIFIED, explicitly unpaid, verified zero cost,
    commercial use allowed, known daily quota, and remaining quota required.
    Premium: active verified Premium entitlement. Paid providers additionally
    require verified positive cost and a configured remaining budget. The
    caller must still use the existing SpendGuard R4.2 before network access.
    """
    if not isinstance(entitlements, dict) or entitlements.get("contract") != CONTRACT:
        raise ProviderRouteDenied("entitlements absents ou invalides")
    if not isinstance(provider_id, str) or not provider_id.strip():
        raise ProviderRouteDenied("provider_id explicite requis")
    source = registry.get(provider_id) if isinstance(registry, dict) else None
    if not isinstance(source, dict) or source.get("status") != "VERIFIED":
        raise ProviderRouteDenied("fournisseur non VERIFIED")
    if source.get("commercial_use") is not True:
        raise ProviderRouteDenied("usage commercial non confirme")
    if source.get("quota_per_day") is None:
        raise ProviderRouteDenied("quota journalier inconnu")
    quota = source["quota_per_day"]
    if isinstance(quota, bool) or not isinstance(quota, int) or quota < 1:
        raise ProviderRouteDenied("quota journalier invalide")

    usage = usage if isinstance(usage, dict) else {}
    used = usage.get("calls_today", 0)
    if isinstance(used, bool) or not isinstance(used, int) or used < 0:
        raise ProviderRouteDenied("compteur de consommation invalide")
    if used >= quota:
        raise ProviderRouteDenied("quota fournisseur journalier atteint")

    paid = source.get("paid")
    if not isinstance(paid, bool):
        raise ProviderRouteDenied("statut de facturation inconnu")

    plan = entitlements.get("plan")
    if plan == FREE:
        if paid is not False:
            raise ProviderRouteDenied("EDGE Free ne peut utiliser aucun fournisseur payant")
        if source.get("cost_status") != "verified_zero" or source.get("estimated_usd_per_call") != 0:
            raise ProviderRouteDenied("cout nul non verifie : fournisseur interdit en Free")
        return {"allowed": True, "plan": FREE, "provider_id": provider_id,
                "billing": "zero_cost_verified", "paid": False,
                "remaining_provider_calls_today": quota - used,
                "execution": "decision_only"}

    if plan != PREMIUM or entitlements.get("status") != "active":
        raise ProviderRouteDenied("abonnement Premium actif requis")
    if paid:
        if source.get("cost_status") != "verified" or not _finite_nonnegative(
                source.get("estimated_usd_per_call")) or float(source["estimated_usd_per_call"]) <= 0:
            raise ProviderRouteDenied("cout payant non verifie")
        if not _finite_nonnegative(estimated_cost_usd) or float(estimated_cost_usd) <= 0:
            raise ProviderRouteDenied("estimation de cette operation requise")
        if not _finite_nonnegative(premium_budget_remaining_usd):
            raise ProviderRouteDenied("budget Premium restant non configure")
        if float(estimated_cost_usd) > float(premium_budget_remaining_usd) + 1e-12:
            raise ProviderRouteDenied("enveloppe IA Premium insuffisante")
        if float(estimated_cost_usd) < float(source["estimated_usd_per_call"]) - 1e-12:
            raise ProviderRouteDenied("estimation inferieure au cout fournisseur verifie")
        return {"allowed": True, "plan": PREMIUM, "provider_id": provider_id,
                "billing": "premium_included_paid", "paid": True,
                "estimated_cost_usd": float(estimated_cost_usd),
                "remaining_provider_calls_today": quota - used,
                "execution": "requires_spendguard_r42"}

    if source.get("cost_status") != "verified_zero" or source.get("estimated_usd_per_call") != 0:
        raise ProviderRouteDenied("cout nul non verifie")
    return {"allowed": True, "plan": PREMIUM, "provider_id": provider_id,
            "billing": "zero_cost_verified", "paid": False,
            "remaining_provider_calls_today": quota - used,
            "execution": "decision_only"}
