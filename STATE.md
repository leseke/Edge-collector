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

## Review persistence task — 2026-11-17
- Development-only additive migration: `cloud/collector/migrations/002_investigation_review.sql`.
- Offline negative/positive tests: `cloud/collector/test/test_review_migration.py`.
- ADR: `docs/adr/002-immutable-human-review.md`.
- Remote migration **not applied**. No authenticated review API or atomic write service implemented.
- CI run #292 (44133553861) was in progress when this snapshot was written; results **not verified**. Do not promote this work without checking its final status.

## Investor home UX V1 — 2026-11-17
- `app/components/MarketDashboard.tsx`: product-first home, progressive price/source disclosure, explicit inactive AI status; reuses existing trusted snapshot.
- `app/dashboard.css`: compact mobile-first card hierarchy and accent styling.
- `agent-harness/test/investor-home-contract.test.mjs`: structural tests; execution **not verified** at time of writing.
- ADR 003: `docs/adr/003-product-first-investor-home.md`.
- No new agent API, paid model call, D1 write, or explicit production deployment was performed by this change.
- CI and real mobile rendering must be verified before promotion.

## Visual V2 / Explorer observed catalogue — 2026-11-17
- Added `/explorer` with client-side search and series filtering of the existing verified snapshot; this is not a complete TCG catalogue.
- Added `AssetImage` client fallback for image-load failures; upstream image availability not yet diagnosed.
- Navigation now links to Explorer and labels existing /mri as Radar; no placeholder Portfolio/Watchlist routes were invented.
- Home links to Explorer; responsive Explorer styles and structural tests added.
- ADR 004 documents alternative options, limitations and reversibility.
- CI execution, Cloudflare deployment, image success, and iPhone rendering **not yet verified** for this lot.
- No model call, paid service, D1 write, purchase or production deployment performed by these changes.
