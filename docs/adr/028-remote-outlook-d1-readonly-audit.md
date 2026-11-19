# ADR 028 — Remote Cloudflare D1 read-only Outlook readiness audit

Date: 2026-11-19
Status: development feature, NOT executed against a remote database.

## Context
EDGE Outlook ingestion passes isolated local Wrangler D1 schema and lease
tests. This does not show whether the expected remote D1 database exists,
whether migrations 003–006 are installed, or whether the operator has a
separate Microsoft Graph connection.

## Decision
Prepare `cloud/collector/tools/outlook-remote-readiness.py` with a
manual-only GitHub Actions workflow:
- Use the existing `CLOUDFLARE_API_TOKEN` secret without printing it.
- List accessible accounts (require exactly one) and look up the single
  `edge-tcg-history` D1 database by exact name. Never choose an arbitrary
  account/database if ambiguous.
- Issue only one hard-coded `SELECT name FROM sqlite_master ...` through the
  Cloudflare D1 query API, ignoring rows and contents of private tables.
- Compare presence of six required tables from migrations 003–006:
  `lbc_alert_messages`, `lbc_listing_observations`,
  `lbc_graph_delta_cursor`, `lbc_oauth_pending`,
  `lbc_oauth_credentials`, and `lbc_sync_lease`.
- Report aggregate readiness and missing table *names*, not API keys,
  account UUIDs, raw SQL errors, mailbox metadata or actual listings.
- No creation, migration, UPDATE/INSERT/DELETE, secrets provisioning,
  consent, cron scheduling, Worker deployment or main merge.
- Fail closed on ambiguous accounts, malformed API responses and errors.

## Constraints
The new workflow uses `workflow_dispatch` only. GitHub may not expose
manual dispatch until this workflow exists on the default branch. We do not
merge or modify main merely to bypass that control.

An existing table's presence is not proof that its schema, triggers, row
contents, encryption keys, permissions or operator access are correct.
A successful SELECT is not live Outlook ingest readiness. Even a complete
schema must still be paired with independently approved Microsoft OAuth,
Cloudflare Access, verified keys and end-to-end read/write tests.

## Verification
Offline Python tests mock exact API routes to verify read-only SELECT,
no data disclosure, missing tables, absent credentials and fail-closed
multi-account/database behavior. Actual remote results are **not claimed**.

## Reversibility
Remove the script and workflow without changing production behavior.
