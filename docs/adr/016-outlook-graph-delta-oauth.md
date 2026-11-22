# ADR 016 — Outlook incremental Graph delta and delegated OAuth

Date: 2026-11-19
Status: DEVELOPMENT, no Microsoft app registered or production activation authorized.

## Context
The user connected Outlook to ChatGPT, which confirms mailbox access in the
conversation but does not give EDGE a reusable OAuth token. Reading every Inbox
page each run would cost time and miss freshness targets. We must not harvest
account-verification emails or leak raw mailbox contents.

## Alternatives
1. Poll entire Inbox with an overlap window; simplest, but growing cost and
   harder missed-page recovery.
2. Use Microsoft Graph message delta with a persisted continuation cursor;
   preserves incremental changes and retries, but opaque cursor confidentiality,
   expiry and folder-scoped semantics need care.
3. Ask users to manually forward emails; rejected because the system is intended
   to be unattended.

## Decision
Choose (2), keeping the Graph client a **pure, injectable module**:
- `leboncoin-delta.mjs` requests Inbox message changes and limits pages per call.
- Each page is parsed and written to the immutable listing ledger before its
  nextLink/deltaLink is checkpointed by a secure cursor store.
- Persisted message IDs prevent duplicate inserts after a crash between data
  commit and checkpoint commit.
- No silent full-rescan on Graph HTTP 410: surface an operational alert.
- Only matching saved-search alerts pass the listing parser.
- `leboncoin-oauth.mjs` supports confidential delegated token refresh via
  `Mail.Read offline_access`; caller injects a *separate* encrypted credential
  store and token refresh must occur server-side.
- Never put credentials, Graph cursor (can contain opaque mailbox state),
  mailbox snippets or user-specific IDs in the frontend or CI logs.

## Security and runtime constraints
- This work intentionally does NOT provision Azure/Entra app registration,
  obtain consent, add Cloudflare secrets, encrypt token stores, expose OAuth
  callback routes, deploy a Worker, enable cron, or modify production D1.
- A production design must use state-bound PKCE authorization code flow with
  CSRF protection, strict registered redirect URI, server-only token exchange,
  least-privilege Mail.Read, encrypted token/cursor storage, tenant isolation,
  revocation/disconnect, token rotation locking and audit/retention policies.
- The current in-memory Graph flow and injection points are suitable for
  testing only until these boundaries are implemented.
- The delta feature captures mail changes, not all Leboncoin search results;
  email count is not the number of imported offers.
- Saved-search excerpts remain LISTING/UNVERIFIED/EMAIL_EXCERPT. Do not use
  to assert an item is on sale now or to calculate realized market prices.

## Completion criteria for this change
Offline tests prove pagination bounds, same-origin delta URL validation,
checkpoint-after-persist, pause/resume, failure rollback of logical cursor,
OAuth refresh request shape and fail-closed rotation. CI must report success.

## Reversibility
Standalone modules and tests only; no deployment, main merge or schema edits
are needed for this incremental iteration. Remove modules to revert.
