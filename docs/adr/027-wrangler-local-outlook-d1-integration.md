# ADR 027 — Wrangler local D1 integration gate for Outlook

Date: 2026-11-19
Status: tested in isolated GitHub Actions, not a remote migration or deployment.

## Context
Prior Outlook tests executed SQL against Python SQLite and simulated D1
objects. They were useful but did not establish that the migrations and
lease SQL execute in Cloudflare Wrangler's D1 local runtime.

## Decision
The existing Cloudflare build workflow now runs
`cloud/collector/test/wrangler-outlook-d1-smoke.sh` immediately after
its standard Wrangler local D1 schema smoke test. This script:
- Reuses the CI-generated Wrangler D1 config and disposable local database.
- Applies migrations 003, 004, 005 and 006 using `wrangler d1 execute --local`.
- Inserts a synthetic Leboncoin saved-search alert and listing under an
  active owner lease, plus encrypted-looking cursor and credential placeholders.
- Replaces the owner lease and attempts stale cursor/credential updates.
- Checks the listing exists and both generations remain unchanged by using
  a CHECK-constrained SQL assertion.
- Uses no Cloudflare token, remote D1, Outlook credentials or external
  Microsoft Graph requests.

## What this proves
SQLite queries and the schema can run with a real Wrangler local D1
emulator. It also exercises the critical lease predicates against that
runtime, rather than trusting mocked statements.

## What it does not prove
Remote D1 concurrency, actual JWT/OAuth callbacks, mailbox identity,
delivered Leboncoin notifications or unattended cron functionality.
A live end-to-end test still requires properly provisioned Cloudflare
Access, a dedicated Entra application and explicit Microsoft user consent.
No branch merge, payment, remote D1 migration or deployment is authorized.

## Reversibility
The CI step and test script can be removed independently from production
code. It creates only temporary runner-local state.
