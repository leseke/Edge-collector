# ADR 024 — Cancel expired Outlook runs before writing Delta checkpoints

Date: 2026-11-19
Status: development-only; no runtime deployment or scheduler.

## Problem
The existing D1 lease excluded overlapping executions, but its owner could
continue asynchronous Graph operations after expiry, allowing a replacement
runner to progress simultaneously. Checking expiry only after completing the
full run was too late to protect the Delta cursor. The existing documentation
already identified this risk.

## Options
1. Keep the final expiry check: insufficient protection against stale writes.
2. Add bounded abort signal and verify D1 lease ownership at each Graph page
   boundary, immediately before immutable writes and immediately before cursor
   advance; keep an exact-token release on shutdown.
3. Use only an in-process mutex: cannot protect different Cloudflare isolates.

## Decision
Choose option 2 as an intermediate hardening layer.
`withOutlookRunLease` supplies an AbortSignal and an asynchronous
`assertActive` callback. This callback checks timer cancellation, local
expiry and durable D1 lock identity/expiry. The Graph reader passes the
signal to fetch and checks ownership before each page, before persisting
and again before moving the checkpoint. The runner wires those primitives
together. Offline tests simulate losing the lock before and after writing
an observation, verifying that the cursor never advances after failure.

## Remaining risk and activation gate
The ownership check and D1 data write are not a single atomic transaction.
A replacement may acquire the lease *between* verification and persistence.
Message writes are idempotent and cursor storage uses compare-and-swap,
but full fencing requires a durable generation included in the same commit,
or a design that cannot overlap due to timeouts and lease renewal. A running
task must be terminated on expiry; Cloudflare runtime interruption tests and
a real D1 integration test remain necessary before live scheduling.

No D1 remote migrations, cron, Microsoft consent, or deployment authorized.
