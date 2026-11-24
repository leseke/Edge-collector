"""EDGE subscription entitlements: fail-closed policy, no payment integration.

A subscription is trusted only when supplied by a future server-side billing
adapter with verified=True. Client-provided plan names are never sufficient.
This module performs no network calls and never authorizes a paid call alone.
"""
from datetime import datetime, timezone

CONTRACT = "edge.subscription_entitlements.v1"
FREE = "free"
PREMIUM = "premium"

# Product limits are policy defaults, not promises of unlimited service.
# Monetary budgets intentionally have no default: Premium paid routing stays
# disabled until an operator configures a real, economically validated budget.
PLAN_LIMITS = {
    FREE: {
        "searches_per_day": 15,
        "investigations_per_day": 3,
        "specialist_tasks_per_inquiry": 3,
        "multi_model": False,
        "paid_providers": False,
    },
    PREMIUM: {
        "searches_per_day": 100,
        "investigations_per_day": 20,
        "specialist_tasks_per_inquiry": 9,
        "multi_model": True,
        "paid_providers": True,
    },
}


class EntitlementError(ValueError):
    pass


def _valid_iso(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def resolve_entitlements(subscription=None, now=None):
    """Resolve Free by default; Premium requires a trusted active server claim."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise EntitlementError("now must be timezone-aware")
    raw = subscription if isinstance(subscription, dict) else {}
    if raw.get("verified") is not True:
        plan = FREE
        status = "free"
    else:
        plan = raw.get("plan")
        status = raw.get("status")
        if plan != PREMIUM or status != "active":
            plan, status = FREE, "free"
        else:
            period_end = _valid_iso(raw.get("period_end"))
            if period_end is None or period_end <= now.astimezone(timezone.utc):
                plan, status = FREE, "expired_or_invalid"
    return {
        "contract": CONTRACT,
        "plan": plan,
        "status": status,
        "limits": dict(PLAN_LIMITS[plan]),
        "paid_provider_access": plan == PREMIUM,
        "multi_model": PLAN_LIMITS[plan]["multi_model"],
    }


def check_feature(entitlements, feature):
    if not isinstance(entitlements, dict) or entitlements.get("contract") != CONTRACT:
        return False
    return bool(entitlements.get("limits", {}).get(feature, False))


def authorize_agent_provider(entitlements, provider):
    """Paywall gate for run_inquiry; paid agents require verified Premium."""
    if not isinstance(entitlements, dict) or entitlements.get("contract") != CONTRACT:
        raise EntitlementError("droits d'abonnement absents ou invalides")
    if getattr(provider, "paid", False) is True:
        if entitlements.get("plan") != PREMIUM or entitlements.get("status") != "active":
            raise EntitlementError("un agent payant exige un abonnement EDGE Premium actif et verifie")
        return "premium_paid_candidate"
    return "non_paid_candidate"
