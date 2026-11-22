# ADR 025 — Atomic D1 fencing for Outlook Delta checkpoints

Date: 2026-11-19
Status: Development branch, unmerged and not deployed.

## Problem
The prior design checked owner lease validity in one database read and
advanced the Delta checkpoint in a later write. A replaced/expired lease
could race between those operations and allow a stale collector to advance
the cursor after losing ownership.

## Decision
The encrypted D1 Delta cursor store now accepts an explicit
`{ownerKey, leaseId}` bound to the collector's active lease.
Both the initial INSERT and every UPDATE use a **single SQL statement** with
an `EXISTS` guard against `lbc_sync_lease`, requiring the same owner and
lease ID and a lease expiry later than the operation timestamp.
A failed guarded insert/update raises
`delta_cursor_lease_lost_or_conflict` and cannot report success.
Existing optimistic `generation` checks remain in place.

The run lease passes its lease ID to the runner, which configures the
encrypted cursor store. This closes the SQL time-of-check/time-of-use
gap for the cursor update *itself*.

## Evidence
Offline JS tests assert the guarded statement and stale-owner refusal.
SQLite migration tests execute both variants with a real SQLite engine,
including missing, expired, replaced and valid lease cases.
Final GitHub CI completion is recorded separately in the PR.

## Still not guaranteed
- A listing observation batch can race with lease expiry; its immutable
  idempotency is not equivalent to a fully fenced DB transaction.
- OAuth refresh token rotation still relies on optimistic generation checks,
  not the lease guard within the same SQL statement.
- A lease holder can be aborted at the network level, but external fetch
  timeouts and Cloudflare runtime behavior need live integration tests.
- No remote D1 database or Microsoft Entra application is provisioned.

## Activation gate
Complete real D1 integration and forced-interruption tests, verify the
independent Microsoft consent and Cloudflare Access operator policy, and
obtain explicit deployment/cron approval. Do not expose OAuth tokens or
promote this PR to main automatically.
