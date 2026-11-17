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

## Product Intelligence V1 — 2026-11-17
- Added read-only dynamic `/explorer/[productId]` detail page with existing integrity-checked market snapshot, product identification, source, observation date, price kind, indicative values, and limitations.
- Explorer tiles link to detail; mobile-first product detail styling added.
- DeepSeek explicitly marked inactive; no AI API, paid request, D1 mutation, purchase or deployment.
- ADR 005 and structural contract tests added.
- CI, build and real mobile rendering **pending verification**.

## MRI public evidence bridge — 2026-11-17
- MRI case summaries are now projected from the SHA-verified public snapshot, including publication titles/URLs, recorded reaction status and financial decision.
- Radar displays available cases and their publication references; product detail matches by exact product ID, with explicit absence when none is linked.
- The inspected public snapshot contained LEGO MRI cases but no `pokemon_card_` case. No AI-generated thesis or financial recommendation was fabricated.
- ADR 006 and structural tests added. CI, build and mobile rendering remain **unverified** for this lot.
- No paid AI calls, purchases, D1 writes or production deployment.

## TCGdex image URL repair — 2026-11-17
- Root cause found in verified raw snapshot: `image` values are extensionless TCGdex image bases (`https://assets.tcgdex.net/fr/base/base1/4`), not direct browser image files.
- Market snapshot now maps trusted extensionless image bases to `/high.webp`; the client tries trusted alternate resolutions before a final fallback.
- Updated existing image-fallback test and added TCGdex URL regression test.
- Network image retrieval, CI and iPhone visual result **not yet verified**. No guarantee the external host will serve images in every network.
- No paid API, database write, purchase or manual production deployment.

## PRODUCT-002C — Evidence from market observations

- Explorer accepts both exact snapshot and legacy Pokémon IDs. A candidate displays the available language, edition, condition, grader and grade evidence with its source. Explicit conflicts reject the match.
- The published TCGdex/Cardmarket observations inspected on 2026-11-17 are indicative aggregates without variant-level evidence. Their variant fields remain unknown and the catalogue page assigns no price to the candidate.
- Verified locally with Node 24: four targeted catalogue bridge tests and strict TypeScript checking of the three changed library modules. Full CI and live UI verification are pending.
