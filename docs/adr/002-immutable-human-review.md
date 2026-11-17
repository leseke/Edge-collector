# ADR 002 — Immutable human investigation reviews

Status: Proposed — development-only migration; client approval required before any D1 application.

## Context
The collector already retains immutable observations. No durable investigation/review schema exists. An AI proposal must remain non-executable, and human acceptance must not authorize purchases. Authentication and HTTP endpoints are not defined.

## Options
A. Add separate append-only investigations, one final review decision per investigation, and append-only audit events.
B. Store a mutable status directly on observations or proposals, updating the same record on approval.
C. Use an external review SaaS.

## Decision
Choose A for the V1 schema, subject to CI. Implement as an independent additive SQL migration, not as a change to the existing collector schema or a deployment.

## Rationale
Preserves market history, enables foreign keys and immutable audit records, prevents two final decisions for the same investigation, and keeps review distinct from trading authority. No paid service or new runtime dependency.

## Consequences
- `investigations` are immutable snapshots, with `status=PENDING_REVIEW`; the effective review state is derived by joining `review_decisions`, not by updating status.
- `review_decisions` have unique investigation and idempotency keys; **retry semantics are not implemented**: a repeated insert fails safely, and a future authenticated API must fetch and compare the original payload before returning an idempotent success.
- `investigation_audit_events` are append-only but not yet transactionally coupled to decisions; the future write service must insert decision and audit event in a single D1 transaction/batch.
- SQL checks prevent `purchase_authorized=1` but cannot establish identity, guarantee JSON proposal semantics, verify source authenticity, or prove event/decision consistency.
- `reviewer_id` is a storage field only, **not proof of authentication**.
- No route, deployment, automatic migration, paid model call, or production access is authorized.

## Reversibility
Before data exists, remove the migration from the dev branch. After data exists, use a separately approved, backup-first migration and retain an audit export; never silently delete reviews. Collector tables are untouched.
