# ADR 026 — Fenced Outlook observations and OAuth token rotation

Date: 2026-11-19
Status: development only; no Microsoft consent or production D1 deployment.

## Problem
The encrypted Graph Delta checkpoint was protected by an atomic D1
lease check, but stale workers could still write immutable listing
observations or rotate refresh tokens after losing the owner lease.

## Decision
The Outlook runner now passes its active owner-key and lease-ID pair
into three server-side persistence boundaries:
1. The Graph Delta cursor store (already guarded in ADR 025).
2. `persistLeboncoinAlerts`: the initial message insert and each listing
   insert use `INSERT OR IGNORE ... SELECT ... WHERE EXISTS` guarded by
   the current owner lease. The D1 batch preserves atomic statement ordering
   and idempotent message/history identifiers.
3. The encrypted OAuth credential store: both initial insert and
   credential-update cases use guarded D1 SQL. Ordinary interactive
   OAuth consent still uses its separately authenticated session flow
   without a collector run lease.

A lost or replaced lease cannot silently report successful persistence
of a previously unseen alert or token rotation. The run lease, cursor
generation and OAuth generation check remain separate additional guards.

## Evidence
- JS regression tests assert lease-bound SQL is emitted for message,
  listing and refresh-token writes.
- Real SQLite tests execute missing/expired/replaced/valid-lease cases
  using migrations 003, 005 and 006.
- Workflow `outlook-leboncoin-tests.yml` runs the expanded regression
  suite and reports CI status separately.

## Remaining limitations
- The timestamp used for the SQL expiry check is sampled just before
  statement preparation. A task could approach expiry between timestamp
  sampling and transaction commit. This is mitigated by active run checks
  and abort signals but still needs Cloudflare/D1 runtime tests.
- A race between the pre-check for an existing message and another
  writer's insert can produce a harmless idempotent conflict. Under a
  lease, this is treated conservatively as a failure to be retried.
- The system still requires independent consent, Access policy,
  secret provisioning, D1 migration and live validation before enabling
  scheduled collection.
- This is NOT a completed-sale feed and must not be used to infer
  live Leboncoin availability or realized prices.

No main merge, database migration or production deployment performed.
