# ADR 018 — Guarded Microsoft consent HTTP adapter (development-only)

Status: DEVELOPMENT; neither routes nor permissions are live in EDGE.
Date: 2026-11-19.

## Context
Existing PKCE, encrypted one-time pending state and refresh-token vault
are modules, not connected to authenticated HTTP handlers. EDGE needs a safe
server-side boundary before a user-facing Connect Outlook control can exist.

## Options
1. Mount endpoints publicly now and rely on their internal state parameters:
   rejected; no reviewed authenticated EDGE session or Microsoft app exists.
2. Implement a gated HTTP adapter, injected verified-session resolver and
   account-scoped stores; keep it unmounted and disabled by default.
3. Use a frontend-only OAuth exchange: rejected; would expose confidential
   client credentials, allow refresh tokens into the browser or weaken
   trusted account binding.

## Decision
Choose (2). `leboncoin-consent-http.mjs` provides two routes:
- `GET /auth/microsoft/start`: requires trusted authenticated session;
  creates one-time PKCE transaction and redirects to Microsoft.
- `GET /auth/microsoft/callback`: requires same session, exactly one code
  and state, atomic state redemption, server-side token exchange, encrypted
  credential storage, and no token in the HTTP response.

The adapter performs origin/method/path checks, no-store/no-referrer headers,
rejects unexpected query parameters, and is disabled by default.
It **must not** read session IDs from user-controlled request headers;
the injected `verifySession` must validate server-controlled authenticated
cookies. `getStores` must derive the mailbox key from that session.

## Requirements not yet satisfied
- Do not mount this module until EDGE authentication and its session cookie
  policy (HttpOnly, Secure, SameSite, rotation and CSRF protection) are
  implemented and independently verified.
- Register a dedicated Microsoft Entra app, verified HTTPS callback URI,
  and account-audience permissions.
- Validate Microsoft Graph identity after consent and ensure correct owner
  binding; a callback alone is not mailbox ownership evidence for a UI.
- Provide permanent key management, refresh-token revocation/disconnect,
  account locking, jobs/credential rotation, D1 deployment and operation.
- Validate behavior under real Microsoft responses and Cloudflare runtime.
- No main merge, production deployment, cron or mailbox access performed.

## Done criterion
Offline tests for disabled default, session checks, cross-origin failures,
callback parameter constraints, one-time state replay, no token disclosures.
Every test must pass in CI; production remains isolated.

## Reversibility
Additive modules/tests on a feature branch, no existing routes changed.
