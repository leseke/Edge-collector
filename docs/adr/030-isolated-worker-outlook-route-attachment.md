# ADR 030 — Mount isolated Outlook consent routes only behind double opt-in

Date: 2026-11-20
Status: source integration only, unmerged and undeployed.

## Problem
Microsoft consent helpers, encrypted D1 storage and a Cloudflare Access
JWT validator had passed unit tests, but the isolated collector Worker
had no HTTP integration point for authorization start or callback.
Without a route attachment there could be no live independent EDGE consent.

## Decision
Attach exactly `/auth/microsoft/start` and `/auth/microsoft/callback`
to the isolated `cloud/collector/src/index.ts` Worker using
`leboncoin-worker-http.mjs`.

The adapter requires two distinct private opt-in values,
`OUTLOOK_ROUTES_ENABLED=true` and `OUTLOOK_CONSENT_ENABLED=true`,
before opening the existing consent handler. By default it returns a
private non-cacheable 404 without touching D1, Cloudflare Access or
Microsoft endpoints. It also returns a generic 404 for missing configuration
or failed signed Access verification, never exposing secret values.
All unrelated routes retain their previous behavior.

Under explicit opt-in, the existing signed Access application JWT
verification, one-operator allowlist, encrypted one-time PKCE state,
Microsoft mailbox identity check and encrypted credentials apply.
Attaching code is **not** itself proof that an Access policy or
Microsoft Entra app has been provisioned.

## Tests
- Offline adapter tests confirm double opt-in, no D1/network work
  without both flags, fail-closed absent settings, absence of Access JWT
  and unchanged non-OAuth path routing.
- The Cloudflare overall TypeScript and Worker build must pass on the
  corresponding pull-request head. Source-code attachment alone is
  not a deployed endpoint.

## Activation barriers
Do not enable either flag before a trusted Cloudflare Access application
is provisioned on the exact Worker hostname and the Access JWT audience
and operator subject are verified. The Microsoft Entra app registration
must use the exact HTTPS redirect URL, and the dedicated consent with
`Mail.Read User.Read offline_access` must be performed by the operator.
Apply and verify remote D1 migrations only after separate authorization.
No new cron or production deployment is part of this change.

## Rollback
Both flags default off. Removing the one import and early routing check
reverts source integration without touching main or the existing Worker.
