# Outlook → Leboncoin ingestion (development / not activated)

Branch: `edge/outlook-leboncoin-ingestion-001`. This is an **additive prototype**.
No production D1 migration, cron, mailbox credential, or public endpoint was activated.

## Confirmed evidence / limits
A connected ChatGPT Outlook account exposed Leboncoin saved-search emails with
a headline result count, partial ad excerpts, numeric listing IDs, URLs and prices.
The saved-search headline does **not** mean EDGE imported that many ads.
Email listings are `LISTING`, availability `UNVERIFIED`, evidence `EMAIL_EXCERPT`.
They are never completed sales and cannot independently certify live availability.

## Components
- `src/leboncoin-email.mjs`: parse converted Markdown or native HTML; Graph pagination guard.
- `src/leboncoin-d1.mjs`: validate + save immutable message/listing rows atomically.
- `src/leboncoin-sync.mjs`: compose Graph read + D1 write, reports partial coverage.
- `src/leboncoin-email-cli.mjs`: local *read-only* Graph check (outputs counts by default).
- `migrations/003_leboncoin_outlook.sql`: proposed append-only D1 tables.
- `test/leboncoin-*.test.mjs`, `test/test_leboncoin_migration.py`: offline verification.

## Tests (offline, no mailbox or credentials)
```sh
node --test cloud/collector/test/leboncoin-email.test.mjs cloud/collector/test/leboncoin-d1.test.mjs cloud/collector/test/leboncoin-sync.test.mjs
python -m unittest discover -s cloud/collector/test -p 'test_leboncoin_migration.py'
```

## Local read-only probe (requires independent Microsoft OAuth consent)
```sh
EDGE_OUTLOOK_GRAPH_ACCESS_TOKEN='<redacted>' node cloud/collector/src/leboncoin-email-cli.mjs
```
The ChatGPT Outlook connector's session cannot be reused as a transferable token
for GitHub Actions or Cloudflare. A dedicated Microsoft Entra/OAuth app, Mail.Read
delegated consent, token renewal, secure storage and an approved runtime are
required before automation can run unattended. Do not put the token in GitHub,
frontend, logs or source code. The command above is illustrative, not an instruction
to expose credentials in shell history; use a secure secret injection mechanism.

## Future activation gate
1. Provision independently authorized OAuth integration and auditable token rotation.
2. Apply migration in test D1, verify foreign-key and atomic-batch behavior.
3. Add idempotent incremental Graph delta or bounded overlap cursor, replay and retry.
4. Schedule collector with status/partial alerts and retention policy; no direct user action.
5. Revalidate ad page, image, stock and final price prior to making a recommendation.
6. Connect verified observations to EDGE UI with source label and snapshot freshness.
7. Review CI and security, then request **separate** deployment approval.

No automatic purchase capability is permitted.

## Incremental and secure checkpoint (new)
- `src/leboncoin-delta.mjs`: Graph Inbox message delta pages. Writes an
  immutable listing batch before saving each nextLink/deltaLink. An incomplete
  page budget reports PARTIAL and retains its continuation.
- `src/leboncoin-delta-store.mjs`: optional server-side AES-256-GCM encrypted
  cursor store on D1. Requires a private 32-byte encryption key (64 hex chars),
  and a pseudonymous mailboxKey per identity. D1 stores nonce/ciphertext only.
  Optimistic generation checks reject stale concurrent writers. Avoid reusing
  keys and change encryption only with a planned migration.
- `migrations/004_outlook_delta_cursor.sql`: optional mutable operational
  checkpoint table; it does not alter append-only price observations.
- `src/leboncoin-oauth.mjs`: delegated confidential-client refresh helper.
  Initial authorization (code+PKCE+state), secure refresh-token persistence,
  CSRF/session protection, secret rotation, and user disconnect are **not**
  implemented; do not enable it against a live Microsoft mailbox yet.
- To test all the new modules, run:
```sh
node --test cloud/collector/test/leboncoin-*.test.mjs
```

The ChatGPT Outlook connection is not a portable Microsoft Graph application
credential; this branch does not authorize unattended Outlook access.

## Microsoft consent and encrypted vault (development V4)
- `src/leboncoin-consent.mjs`: PKCE S256 authorization URL, one-time
  state bound to an authenticated EDGE session, expiration, code exchange.
- `src/leboncoin-oauth-store.mjs`: AES-GCM encryption at rest for pending
  PKCE verifier/session state and refresh tokens. Uses mailbox-bound AAD,
  atomic `DELETE RETURNING` on consumed state and CAS token rotation.
- `migrations/005_outlook_oauth_secure.sql`: proposed D1 tables.
- ADR 017: alternatives, trust boundaries, activation and revocation gates.
- No Microsoft app registration, live OAuth callback, independent consent,
  production credential store or Cloudflare cron has been enabled.
- CI validates offline fixtures only. Microsoft Graph access from ChatGPT
  cannot be inherited by this application.

For production the authenticated callback endpoints and mailbox identity
binding remain mandatory; do not interpret these modules as a usable login UI.
