# EDGE state — manually verified snapshot

As of 2026-11-17. This file is maintained manually until a generator and its provenance are implemented; **not auto-generated**.

Branch: `edge/cloudflare-migration-001`. Main and production unchanged by this governance task.

## Evidence inspected
- `cloud/collector/schema.sql`: immutable D1 observations and collection errors; no investigation/review tables.
- `agent-harness/proposal.mjs`: validated model proposal; purchaseAuthorized false.
- `agent-harness/investigation-review.mjs`: citation metadata matching, not semantic fact verification.
- `agent-harness/investigation-pipeline.mjs`: bounded cursor pagination and injected adapter.
- `agent-harness/deepseek-adapter.mjs`: opt-in model transport.
- `package.json`: existing Next.js/OpenNext dependencies; target static SPA not yet adopted.

## Verification
Prior CI run #265 (44109240876) returned success for cloudflare, native Cordis smoke, synthetic D1 fixture, and real D1 read-only jobs. This does not verify governance files or a production SPA. Current task tests and CI must be recorded separately after execution.

## Open
Approve V1 contracts, resolve SPA migration, design human review persistence and auth, confirm data transfer/cost policy. No automatic purchase and no production deployment.
