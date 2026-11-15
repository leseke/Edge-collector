"""Trusted per-user inquiry entry point with persistent quota reservation.

This is a server-side service boundary, not an HTTP route or authentication
system. Callers MUST pass a user_id and subscription claim obtained from trusted
server-side identity/billing code; never forward browser-supplied values.
"""
from datetime import datetime, timezone

from intelligence.subscription_entitlements import (
    FREE, resolve_entitlements, authorize_agent_provider,
)
from intelligence.usage_meter import reserve_usage, UsageLimitExceeded


class InquiryAccessDenied(RuntimeError):
    pass


class InquiryQuotaExceeded(InquiryAccessDenied):
    pass


def run_user_inquiry(
    question,
    corpora,
    report_store,
    *,
    user_id,
    request_id,
    usage_store,
    provider,
    subscription_claim=None,
    now=None,
    spend_guard=None,
    send=None,
    max_operations=1,
    allow_test_store=False,
):
    """Reserve a daily investigation unit, then run the existing inquiry engine.

    EDGE Free is deliberately restricted to the locally validated Ollama
    adapter. Paid providers remain Premium-only and are checked again by the
    inquiry engine's SpendGuard path. The reservation happens before model
    execution to prevent concurrent quota oversubscription. A failed provider
    attempt still consumes one attempt.

    Reusing request_id is quota-idempotent, but callers should also deduplicate
    in-flight HTTP requests if they need response-level idempotency.
    """
    for value, label in ((user_id, "user_id"), (request_id, "request_id")):
        if not isinstance(value, str) or not value.strip():
            raise InquiryAccessDenied(label + " serveur requis")
    if usage_store is None or not callable(getattr(usage_store, "atomic_reserve", None)):
        raise InquiryAccessDenied("un stockage transactionnel des quotas est requis")
    if getattr(usage_store, "test_only", False) and not allow_test_store:
        raise InquiryAccessDenied("stockage mémoire réservé aux tests")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise InquiryAccessDenied("horodatage avec fuseau requis")

    entitlements = resolve_entitlements(subscription_claim, now=now)
    try:
        authorize_agent_provider(entitlements, provider)
    except ValueError as exc:
        raise InquiryAccessDenied(str(exc)) from exc

    if entitlements["plan"] == FREE:
        if getattr(provider, "paid", None) is not False or getattr(provider, "name", None) != "ollama_local":
            raise InquiryAccessDenied(
                "EDGE Free est limité au fournisseur local Ollama vérifié"
            )

    period = now.astimezone(timezone.utc).date().isoformat()
    limit = entitlements["limits"]["investigations_per_day"]
    try:
        reservation = reserve_usage(
            usage_store, user_id, period, "investigation", limit, request_id
        )
    except UsageLimitExceeded as exc:
        raise InquiryQuotaExceeded("quota quotidien d'enquêtes EDGE atteint") from exc

    # Import lazily to keep this boundary independently testable.
    from intelligence.inquiry import run_inquiry

    result = run_inquiry(
        question,
        corpora,
        report_store,
        now=now,
        provider=provider,
        spend_guard=spend_guard,
        send=send,
        max_operations=max_operations,
        subscription_claim=subscription_claim,
    )
    if isinstance(result, dict):
        result["usage"] = {
            "metric": "investigation",
            "period_utc": period,
            "limit": limit,
            "reservation_key": reservation["key"],
            "reservation_bucket": reservation["bucket"],
            "attempt_consumed": True,
        }
    return result
