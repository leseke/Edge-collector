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

## Catalogue price coverage

Card detail reads the dated EUR low-price indication from the Cardmarket block of its existing TCGdex response, independently of the tracked-card feed. Prices older than 48 hours carry a freshness warning. The indicator is not a completed sale or variant-level evidence. Existing routes and D1 schema are unchanged. Card IDs with dots can be opened from catalogue search and set browsing.

## DeepSeek price analysis preparation

The agent harness can select sourced Pokémon price changes from commercial events. It defaults to a no-network dry run and can be tested with an injected DeepSeek transport. Three targeted tests passed. Published snapshot 44194865602-1 yielded no price events. No recurring job, paid call, or publication of model commentary is active in this step.

## Automatic price changes without model calls

Tracked Pokémon detail pages can display a deterministic comparison from published commercial events. The input is hash-checked and matched to the current observation; invalid or unavailable events leave the price display available. Older snapshots are supported through their capture manifest. No D1 changes, new routes, model call or scheduled job are required.

## Expanded Pokémon commercial collection

The development configuration increases the fixed Pokémon targets from two to six by adding Mewtwo, Tortank, Noctali VMAX and Ectoplasma VMAX. The total bound rises from 16 to 20 to retain five discovery slots. The collector fetched all six live TCGdex prices successfully and 26 commercial tests passed locally. These local observations have not been published. Scheduled collection still runs from the default branch and must adopt this configuration before it builds history for the new cards.

## Explorer tile prices

Search and set tiles request dated Cardmarket indications from TCGdex as they approach the viewport. The local route returned all four prices for basep-14, ecard1-20, ex13-24 and swsh10.5-030 against live TCGdex. No Google model calls are required. Preview UI verification is pending.

The price route accepts all 17 documented TCGdex locales. It uses dated Cardmarket EUR prices (including holo when needed), then TCGplayer USD prices with the source and variant identified. Cards without a suitable price return null.

Catalogue detail exposes user-initiated Vinted and Leboncoin searches with the card identity, plus a ready-to-copy Google AI Studio query. No Gemini API integration or automated marketplace observation is enabled by these links.

## Pokémon liquidity pilot

The MRI dashboard shows the age, scoped observed listing inventory and paid-sale counts over 7/30/90 days for the same card variant. The only reviewed case currently shipped is Noctali VMAX 215/203 FR Unlimited PCA 9 (one documented historical paid sale, no comparable listing snapshots). No drop rate, total market count or trading recommendation is inferred. Automated marketplace collection and Radar alerting are not connected.

The pilot prioritizes a tightening candidate only when a listing capture at most seven days old has a comparable earlier capture at most 30 days apart and fewer observed listings, with at least two documented paid sales in each of the current and previous 30-day windows and stable or rising sale count and median. These are pilot review criteria. No reviewed case currently qualifies, and marketplace ingestion remains unconnected.

The liquidity pilot can ingest reviewed Vinted and Leboncoin inventory captures by exact card variant, capture day, and canonical search scope. It accepts direct listing IDs, deduplicates URLs and rejects search landing pages as individual listings. The capture corpus is empty until verified observations can be supplied. A native email alert is a lead and cannot populate an inventory snapshot on its own.
