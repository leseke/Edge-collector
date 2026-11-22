# ADR 031 — Authenticated operator-triggered Outlook ingest (disabled by default)

Date: 2026-11-20
Status: feature branch, not merged, deployed, or enabled.

## Goal
An independent Microsoft OAuth flow and D1 runner already exist, but
there was no callable bridge between the signed Cloudflare Access operator
and the per-owner Outlook collection function. Until this path is attached,
the OAuth credentials cannot be used by an authorized EDGE operator to
validate real Leboncoin ingestion.

## Choice
Attach a single `POST /internal/outlook/sync` route to the isolated Worker.
The handler remains invisible unless **all four** server-only flags are
exactly `true`:
- `OUTLOOK_ROUTES_ENABLED`
- `OUTLOOK_CONSENT_ENABLED`
- `OUTLOOK_INGEST_ENABLED`
- `OUTLOOK_MANUAL_SYNC_ENABLED`

After opt-in, it requires exact HTTPS same-origin with the registered
Microsoft callback origin, an exact JSON content type, empty `{}`
payload, and rejects cross-site fetches, query parameters, user-provided
owner keys or alternate authorization headers. The request body is
bounded to 16 bytes before parsing.

The handler cryptographically verifies a Cloudflare Access app JWT
against pinned team keys, audience and the one-subject allowlist. It
derives the stable owner key ONLY from the verified JWT and runs
`runOutlookLeboncoinCollection` with a maximum of three Graph delta
pages per invocation. The existing D1 per-owner lease, encrypted
OAuth vault, verified Microsoft Graph account ID, idempotent immutable
observations and encrypted cursor protect the collection.

The browser receives aggregate counters only, never mailbox addresses,
refresh/access tokens, message bodies or raw listing details. Failed
network, D1 and identity paths return generic errors, and a concurrent
collector returns BUSY.

## Safety and limitations
- No service is deployed or scheduled by this PR. Flags remain absent/off.
- This manual operation is a *diagnostic bridge*, not the autonomous cron,
  user-facing trading decision engine or production readiness proof.
- It depends on a separately provisioned Microsoft Entra app, independent
  user consent, Cloudflare Access and verified remote D1 migrations.
- A Cloudflare Access JWT and same-origin policy are essential: never
  enable the route on an unprotected hostname or trust request owner keys.
- The operator's registered origin must match the deployed Worker host.
- The response reflects mail-alert excerpts only, not confirmed active
  Leboncoin stock or completed sales.
- The caller must have a trusted same-origin UI; a public browser helper
  is not added in this iteration.

## Verification
Node tests confirm four independent opt-ins, path/method/origin/content
restrictions, bounded body size, rejection before authentication/D1,
owner-key derivation through a verified identity callback, BUSY and
redacted failure results. Cloudflare build and full tests run on
GitHub CI; results must be confirmed before deploying.

No main merge, independent OAuth permission, database migrations,
scheduled collection or real mailbox reads were performed.
