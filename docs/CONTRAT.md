# EDGE contracts — observed vs proposed

Status: **DRAFT**. Never interpret a proposed signature as a deployed endpoint.

## Existing D1 schema (verified from cloud/collector/schema.sql)
- collection_runs(run_id TEXT PK, started_at TEXT, finished_at TEXT?, status RUNNING|OK|PARTIAL|FAILED|EMPTY, attempted, succeeded, failed).
- observations(observation_id TEXT PK, run_id TEXT FK, product_id TEXT, source TEXT, observed_at TEXT, price_cents INTEGER?, currency TEXT?, availability TEXT, price_kind LISTING|AGGREGATE|COMPLETED_SALE, source_url TEXT, payload_sha256 TEXT, source_updated_at TEXT?).
- collection_errors(error_id TEXT PK, run_id TEXT FK, product_id TEXT, source_url TEXT, occurred_at TEXT, reason_code TEXT).
- Observation and error rows reject UPDATE/DELETE via triggers. One observation per (run_id, product_id); one error per (run_id, product_id). **No review_queue or investigations table is established by this schema.**

## Existing JavaScript proposal signature (verified from agent-harness/proposal.mjs)
`validateProposal(input: unknown) -> { productId: string, thesis: string, catalysts: string[], risks: string[], entryHypothesis: string, exitHypothesis: string, evidence: Evidence[], status: "PROPOSAL_REQUIRES_HUMAN_REVIEW", marketDataVerified: false, purchaseAuthorized: false }`.
Evidence: `{kind: "FACT"|"WEAK_SIGNAL"|"INFERENCE"|"BET", claim: string, sourceUrl?: string, observedAt?: string}`; FACT requires HTTPS source URL and parseable timestamp.
`reviewInvestigation(rawProposal, trustedExport, now?)` matches FACT source URL and timestamp metadata against provided D1 rows; `claimSemanticsVerified: false`, `purchaseAuthorized: false`. Invalid facts may result in `NEEDS_EVIDENCE_CORRECTION`.
`runInvestigations(trustedExport, generate, {now?,cursor?,maxProducts?})` handles at most 20 products per page, returns `processedProducts`, `remainingProducts`, `nextCursor`, `results`, `purchaseAuthorized: false`.

## Proposed TypeScript domain signatures (NOT implemented)
- `Observation`: immutable D1 observation; `price_kind` discriminates price provenance.
- `Investigation`: stable id, productId, createdAt, evidenceSnapshotRef, status.
- `Evidence`: kind, claim, optional citation metadata, independent verification state.
- `Proposal`: thesis, catalysts, risks, entryHypothesis, exitHypothesis, evidence; never an order.
- `ReviewDecision`: investigationId, reviewerId, decision APPROVE|REJECT, rationale, decidedAt.
- `AuditEvent`: eventId, aggregateId, actor, eventType, occurredAt, payloadDigest.

## Proposed routes (NOT implemented)
- `GET /api/investigations/:id`: authenticated investigation read.
- `GET /api/reviews/pending`: authenticated reviewer queue.
- `POST /api/reviews/:id/decision`: authenticated, authorized, idempotent human review. Approval means proposal acceptance only, never spending.
- `GET /api/observations?productId=&limit=`: read-only bounded observations.

Request/response JSON, authorization policy, schema migrations and error codes are **undecided**; do not implement routes from these placeholders.

## Critical edge cases before API coding
Duplicate decision submissions; reviewer identity spoofing; stale snapshots; malformed dates/currencies; evidence from another product; synthetic source contamination; request replay; oversized payload; unavailable model; rate limits; schema migration compatibility; immutable history.
