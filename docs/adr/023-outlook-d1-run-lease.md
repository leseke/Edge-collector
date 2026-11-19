# ADR 023 — Per-owner D1 run lease for Outlook sync

Status: development only. 2026-11-19.

## Context
Even with immutable mail observations and a cursor compare-and-swap, two
simultaneous scheduled runs may independently refresh the same token and
advance a mailbox cursor. This risks token rotation collisions and
out-of-order checkpoints.

## Options considered
1. Depend on the scheduler to avoid concurrent dispatch: simple, but retries
   and manual invocations can overlap.
2. Acquire a D1 transactional owner lease before token refresh and Graph reads,
   and release only the current lease holder's matching token.
3. Use an in-memory mutex: not durable across Cloudflare isolates.

## Decision
Choose (2). The new `006_outlook_run_lease.sql` migration defines one lock per
pseudonymous owner key. `leboncoin-run-lease.mjs` uses a single D1 UPSERT
with a lease-expiry condition, returns BUSY without accessing Microsoft when
another run is active, and releases with an exact lease token. The guarded
`leboncoin-runner.mjs` acquires this lease before accessing the credential
store and Graph.

The fixed 120-second lease is a provisional protection for bounded operations;
it is **not** a substitute for a hard execution timeout, clock discipline,
continuation heartbeats and safe cancellation. Before activation, align the
lease with the Cloudflare execution budget and Graph request timeouts; a run
that continues after expiry must not commit further checkpoints.

## Tests and operational requirements
Offline tests cover competing acquisition, release on success/failure,
expired lease behavior and stale owner release. Real D1 compatibility and
end-to-end forced-interruption tests are still required. The database
migration has NOT been applied remotely.

## Reversibility
All additions are isolated to the development branch. Existing deployed
Worker routes, cron and public UI remain unchanged.
