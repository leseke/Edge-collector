# ADR 037 — Authenticated, read-only Outlook activation diagnostics

Date: 2026-11-20
Status: development-only, not enabled or deployed.

## Problem
EDGE's separately developed Microsoft OAuth, Cloudflare Access, encrypted
D1 and scheduled ingestion components lacked a safe operator-facing way to
distinguish missing configuration from unverified external infrastructure.
A legacy activation check also reported "ready_for_live_consent" true
with consent enabled even when OAuth HTTP routes were disabled.

## Decision
- Add isolated Worker GET `/internal/outlook/readiness`, opt-in only
  with BOTH `OUTLOOK_ROUTES_ENABLED=true` AND
  `OUTLOOK_DIAGNOSTICS_ENABLED=true`.
- Require HTTPS, exact origin matching the server-configured Microsoft
  redirect host, no query string, no user-supplied owner key or alternate
  authorization header.
- Verify the fully signed Cloudflare Access application JWT with the
  pinned team issuer, audience and exactly one allowlisted subject.
  Do not expose the existence of configuration variables to unauthenticated
  callers. Fail closed with a private 404.
- Once authenticated, show only whether binding names are valid/present,
  which feature switches are on, and which components require independent
  proof. Never expose secret values, operators' IDs, mailbox identities,
  message bodies or D1 row contents.
- Perform **no D1 SQL, Microsoft Graph calls or Cloudflare API management
  lookups** during the diagnostic, other than the Access public key request
  needed for signed identity verification.
- Mark Microsoft registration, Access operator policy, remote D1 migration,
  real user consent and production collection `NOT_VERIFIED` regardless of
  the presence of environment variables. Presence is not proof.
- The underlying activation checker now also requires
  `OUTLOOK_ROUTES_ENABLED=true` before saying consent configuration is ready.

## Verification
Offline tests cover disabled routes with zero external work, unauthenticated
requests, wrong origin/method/query/alternate credential, sanitized successful
response and missing bindings without SQL. The endpoint is a status
diagnostic, not a mechanism to authorize the first deployment.

## Operational boundary
The code remains inside the draft branch. No new Cloudflare policy,
Microsoft Entra registration, D1 remote operation, active flag, cron or
production deployment is performed. An operator must separately validate
the official sender domain from real consented Graph mail metadata,
Microsoft delegated permissions, Cloudflare Access policy and remote D1
schema before an approved first import.
