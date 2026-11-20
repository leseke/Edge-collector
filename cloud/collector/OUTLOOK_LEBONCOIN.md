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

## Authenticated HTTP consent adapter (development V5)
- `src/leboncoin-consent-http.mjs` defines feature-disabled-by-default
  authorization start and callback handlers, with strict origin/path/method
  checking and trusted-session callback injection. This module is **not
  mounted** in `src/index.ts` or production UI.
- `test/leboncoin-consent-http.test.mjs` verifies session enforcement,
  callback replay rejection, no tokens in HTTP response, and malformed
  callback handling.
- ADR 018 records the reason endpoints remain unmounted: EDGE must first
  provide a hardened, authenticated session resolver and a verified mailbox
  ownership binding. The existing ChatGPT Outlook connection cannot substitute.

## Verified Microsoft account binding (development V6)
- `src/leboncoin-identity.mjs` queries delegated Graph `/me` after the
  Microsoft authorization code exchange. It extracts only an opaque account ID.
- The guarded callback requires Graph identity verification before persisting a
  refresh token. An identity error leaves the token vault unchanged.
- Encrypted credentials keep a previously verified Graph identity during token
  rotation; reconnecting a different account fails rather than silently
  replacing the connection.
- The session-derived mailbox key still requires a fully authenticated EDGE
  session implementation; no actual user account was bound or authorized by
  these changes. See ADR 019.

Identity verification via Microsoft Graph /me requires delegated User.Read in addition to Mail.Read and offline_access. Independent Microsoft user consent has not yet been performed.

## Delta compatibility and activation preflight (development V8)
- The delta URL validator now accepts both documented Microsoft Graph forms:
  `/me/mailFolders/{id}/messages/delta` and
  `/me/mailfolders('id')/messages/delta`, without accepting unrelated hosts.
- `src/leboncoin-activation-check.mjs` provides a non-secret configuration
  diagnostic. It reports missing *binding names*, not secret values.
  Configured environment variables do not establish that Microsoft consent,
  a Cloudflare Access policy, D1 migrations, or production collection exist.
- No remote Access policy, Microsoft Entra application or schedule was
  provisioned in this iteration. See ADR 021.

## Full consented collection composition (development V9)
- `src/leboncoin-runner.mjs`: a **single opt-in invocation** combining the
  encrypted OAuth credential vault, refresh, Graph /me identity check,
  bounded Delta ingestion, immutable D1 records and encrypted cursor.
- Collection explicitly requires `OUTLOOK_INGEST_ENABLED=true`, a verified
  account ID, a valid independently consented Microsoft refresh credential,
  a trusted server-derived owner key, D1 and encryption secrets. Otherwise
  it fails closed with no Graph collection. Not wired to cron or live HTTP.
- `OUTLOOK_DELTA_ENCRYPTION_KEY` is a separate 32-byte hex secret from the
  OAuth encryption key and is now checked by activation diagnostics.
- The general Cloudflare collector test failure on a previous commit was
  traced to a flaky signature corruption fixture, corrected to mutate the
  first significant Base64URL signature character. See ADR 022.

## Concurrency protection (development V10)
- `src/leboncoin-run-lease.mjs` requires a single-owner D1 lease before
  accessing Microsoft credentials and Graph. A simultaneous run returns BUSY
  without collecting. Release uses the exact lease owner token.
- `migrations/006_outlook_run_lease.sql` defines the operational lease table.
- `test/leboncoin-run-lease.test.mjs` and
  `test/test_leboncoin_lease_migration.py` cover acquisition, exclusion,
  stale-lease recovery and safe release.
- Do not schedule yet: a per-run timeout, renewal strategy and real D1
  concurrency test are prerequisites. See ADR 023.

## Active lease checks and fetch cancellation (development V11)
- The per-owner D1 lease now supplies an AbortSignal, and durable ownership
  verification is performed before Graph pages, listing persistence and cursor
  checkpoints. A cancelled/expired/lost lease cannot intentionally advance a
  checkpoint.
- These checks are not atomic with an observation write. Real D1 and
  Cloudflare race/cancellation tests remain required before activation.
- ADR 024 documents the residual time-of-check/time-of-use gap and the
  necessary stronger fencing or reliable bounded run cancellation.

## Atomic Delta cursor fencing (development V12)
- `src/leboncoin-delta-store.mjs` now accepts an active D1 owner lease
  token. In both INSERT and UPDATE cases, checkpoint writes use a **single
  atomic SQL statement** requiring the matching unexpired lease token.
  If the token was lost/replaced, no checkpoint is advanced.
- `src/leboncoin-runner.mjs` passes the lease ID supplied by the owner lock.
  Existing generation compare-and-swap remains active.
- JavaScript tests and actual SQLite compatibility tests cover missing,
  expired, and replaced leases. See ADR 025.
- This closes the race for cursor **writes**, not all other operations:
  observation batches and OAuth refresh still require further fencing or
  a proven bounded execution model. No remote D1 test or live deployment.

## Observation and OAuth SQL fencing (development V13)
- The runner passes one active `{ownerKey, leaseId}` through the Graph
  Delta cursor, immutable alert/listing writer and encrypted OAuth vault.
- Alert and listing INSERT statements require the matching D1 lease in
  SQL. Token insert/rotation likewise checks the same owner lease and
  continues to use generation compare-and-swap.
- The guarded messages/listings still represent email-sourced asking
  prices, not concluded sales or guaranteed available listings.
- Offline Node tests and SQLite migration tests validate missing,
  replaced, expired and valid lease scenarios. The Cloudflare D1
  runtime and Microsoft Graph remain untested against live credentials.
- See ADR 026 for the sampled-time lease-expiry limitation and
  conservative duplicate handling. Do not enable unattended polling
  without independently approved infrastructure.

## Wrangler local D1 integration test (development V14)
- The Cloudflare build CI now executes
  `bash cloud/collector/test/wrangler-outlook-d1-smoke.sh` using a real
  disposable Wrangler `d1 execute --local` database.
- All four Outlook migrations (003–006) are applied locally.
  The test inserts synthetic alert, listing, cursor and credential rows
  under a valid owner lease; then replaces the lease and verifies stale
  cursor and refresh-token updates leave existing generations unchanged.
- This is actual local D1 execution, not remote production D1, not an
  actual Microsoft consent or a real Leboncoin email import. See ADR 027.

## Remote D1 schema audit (development V15)
- `tools/outlook-remote-readiness.py` is a **read-only audit** for the
  remote Cloudflare D1 schema. It lists the account/database and asks
  `sqlite_master` only for the names of six required Outlook tables,
  never their contents. It prints no token, mailbox ID or D1 UUID.
- The `outlook-d1-readonly-audit.yml` workflow is **manual-only**. It
  has not been run or given remote D1 write permissions in this iteration.
  GitHub may require the workflow on the default branch before dispatch
  becomes available; do not merge this draft PR merely to activate it.
- Offline tests cover missing database/tables, ambiguous scope and
  response redaction; a schema listing does NOT prove correct table shape
  or real Microsoft authorization. See ADR 028.

## End-to-end cancellation of Outlook read-only collection (development V17)
- `leboncoin-runner.mjs` propagates the active D1 lease cancellation
  signal and owner check through Microsoft refresh-token requests, Graph
  /me identity attestation and Graph Delta pages.
- The token refresh path refuses to rotate stored credentials or start
  the Graph consumer when the D1 lease has already been lost. D1 lease
  fencing and encrypted credential CAS remain required.
- Cooperative cancellation does not replace provisioning Microsoft
  Entra, Cloudflare Access, remote D1 migrations, user consent and live
  operational testing. See ADR 029.

## Isolated Worker consent route attachment (development V19)
- `cloud/collector/src/index.ts` now delegates the exact
  `/auth/microsoft/start` and `/auth/microsoft/callback` paths to
  `src/leboncoin-worker-http.mjs` **in source only**.
- Both `OUTLOOK_ROUTES_ENABLED=true` and `OUTLOOK_CONSENT_ENABLED=true`
  must be set on the isolated Worker. Otherwise each route returns a
  generic private 404 **before** resolving any credentials, D1, Cloudflare
  Access or Microsoft request. Unknown routes fall through.
- If explicitly enabled, the existing Cloudflare Access RS256-signed operator
  verification and the one-time PKCE state flow still apply. A missing
  environment binding or absent/invalid Access JWT fails closed.
- The entire PR is still UNDEPLOYED and no feature flag, Access policy,
  Microsoft registration, independent consent, D1 migration, or remote
  ingestion is configured in production. No collector cron is added.
- Earlier sections documenting these routes as unmounted describe V5-V18;
  this V19 attaches them behind the new **second opt-in**. The complete
  operator authorization procedure must be verified before either flag
  is enabled on an approved deployment.
