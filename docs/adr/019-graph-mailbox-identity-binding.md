# ADR 019 — Verify Microsoft Graph mailbox identity before OAuth persistence

Date: 2026-11-19
Status: development only; OAuth HTTP routes remain unmounted and disabled.

## Context
A successful authorization-code exchange only establishes that Microsoft issued
a delegated token. It does not prove which mailbox EDGE is attaching to which
authenticated application account. A first-time consent and a reconnect must
not allow an incorrect account to replace an existing mailbox authorization.

## Alternatives
1. Trust the email string sent by the browser: rejected as forgeable.
2. Decode token claims locally without validated audience/signature: rejected
   as unsuitable evidence for the Graph mailbox being accessed.
3. Request Microsoft Graph `/me` with the delegated access token and persist
   its opaque ID under the server-verified EDGE principal. Reject mismatches.

## Decision
Choose (3), with delegated Mail.Read and User.Read (Graph /me profile identity):
- `leboncoin-identity.mjs` queries `GET /v1.0/me` and validates Graph's
  opaque account ID. It returns no email address or display name.
- `leboncoin-consent-http.mjs` requires this identity verification before
  an OAuth refresh token may be saved, failing closed on Graph errors.
- `leboncoin-consent.mjs` supports the identity check hook between token
  exchange and encrypted credential storage.
- `leboncoin-oauth-store.mjs` encrypts the account ID alongside the
  refresh token, preserves it across rotations, and blocks changes to an
  existing verified account ID.
- The injected `getStores(session)` MUST identify the actual authenticated
  EDGE owner, not any browser-supplied mailbox key. First-time connection
  should show the confirmed Microsoft account identity to that authorized
  owner before activation of unattended polling; this UI is not built yet.

## Remaining gate
No Microsoft Entra app has been registered, no verified production EDGE
authentication/session exists, and no live permission consent has occurred.
No endpoints are mounted. Confirm D1/Cloudflare runtime, implement secure
session handling, disconnect/revocation and live user confirmation before
enabling any worker, cron or UI.

## Tests and reversibility
Offline tests cover Graph identity success, missing/unauthorized identity,
expected-account mismatch, and denial of token storage on failed identity.
All additions stay on the feature branch and can be reverted without
modifying current deployed services.
