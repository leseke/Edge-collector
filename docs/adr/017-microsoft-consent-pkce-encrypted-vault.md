# ADR 017 — Microsoft OAuth PKCE consent and encrypted temporary state

Status: **development only**. No public OAuth routes or production integration enabled.
Date: 2026-11-19

## Context
ChatGPT's connected Outlook session is not a portable credential for EDGE.
An independent Microsoft Entra app registration, authenticated EDGE user
session, explicit delegated user consent and secure server-side credential
storage are required for unattended Outlook ingestion.

## Options evaluated
1. Ask operators to paste access tokens: violates safe long-term management,
   refresh, least-privilege and no-manual-input goal.
2. Use a server-side authorization code flow with PKCE S256, one-time CSRF
   state, session binding and encrypted D1 persistence.
3. Request broad application mailbox permissions: excessive reach and admin
   consent complexities; not justified for a personal saved-search mailbox.

## Decision
Choose option 2. Implement standalone primitives:
- `leboncoin-consent.mjs`: begin consent with random verifier/state, SHA256
  S256 challenge; finish by matching session binding and consuming state once
  before confidential server-side authorization-code exchange.
- `leboncoin-oauth-store.mjs`: D1 pending state and delegated refresh-token
  encrypted at rest with AES-256-GCM, distinct domain/AAD, per-mailbox key.
- `005_outlook_oauth_secure.sql`: D1 storage schema. Use SQLite
  `DELETE ... RETURNING` for atomic single-use state consumption.
- `leboncoin-oauth.mjs`: exchange stored refresh token for short-lived access
  token, persist rotated refresh token *before* running the sync.
- `leboncoin-delta.mjs`: resume incrementally and checkpoint after each
  successfully persisted page.

## Public callback and deployment gates — still NOT implemented
- Register a dedicated Microsoft Entra application; configure the correct
  personal Microsoft account audience and exact HTTPS callback URI.
- Implement authenticated EDGE session with HttpOnly Secure SameSite cookies,
  login CSRF protections, server-only /start and /callback handlers, strict
  redirect URI and host checks, callback rate limits, OAuth error handling.
- Bind the credential and cursor record to a confirmed Microsoft identity,
  not merely to an unverified user-entered account string.
- Provision mailbox-specific pseudonymous key, 32-byte server-only encryption
  key, D1 migrations, secret rotation and user disconnect/revocation route.
- Verify Microsoft app consent restrictions, retention/deletion policy and
  privacy, durable job locking, refresh-token and delta concurrency handling.
- Confirm D1 compatibility and Cloudflare Worker runtime with live integration
  tests. CI fixtures do not prove production consent or access.
- Expose no purchase action or autonomous financial transaction.
- Require explicit deployment approval; keep PR draft and main untouched.

## Completion criteria for development primitives
Offline tests must prove proper PKCE challenge parameters, CSRF replay
rejection, session substitution rejection, expired state rejection, strict
HTTPS callbacks, encryption at rest, CAS rotation, SQL one-time redemption
and negative secret-store failures.

## Reversibility
All files are additive within the isolated development branch. Remove
modules/migration without affecting deployed systems.
