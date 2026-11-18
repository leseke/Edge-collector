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

## Leboncoin watch searches and manual leads

The MRI dashboard links to the six configured searches and can retain direct Leboncoin listing links in local browser storage. Leads are deduplicated by listing ID and query strings are removed before storage. They do not populate reviewed inventory captures or sales. Outlook alert delivery and automated ingestion still await verification.

## Manual listing analysis

Saved Leboncoin leads can be evaluated with a user-entered asking price, acquisition fees, available budget, target gain, and hypothetical net resale. The result shows cash needed, hypothetical gain and a conditional maximum asking price. Missing fees/resale block the maximum. Values are session-only. No offer or transaction data are fetched or inferred from the URL.

The listing analysis no longer requests a resale price. For a user-confirmed exact variant, the short-term calculation consumes reviewed paid sales within 90 days and requires two observations. A sale minimum-to-median range is reported gross; the entry cap uses the low end and a transparent 10% resale fee assumption. The long-term decision can flag a vulnerable entry or a speculative watch using past-sale downside and the existing supply-tightening signal. An annual price forecast is not emitted. No automatic Leboncoin identity matching or paid sales ingestion is enabled.

## Reviewed paid-sales coverage — 2026-11-18

The Radar consumes nine sourced Graded Card Center sales over five French Unlimited card and grade combinations. Each item page explicitly shows a paid status. Ectoplasma VMAX 157/264 has one paid sale within 90 days per covered grade, so neither grade has a short-term resale quote. Its PSA 10 grade has three dated sales spanning over 90 days and supports a historical downside scenario. These observations do not establish total market volume or a future price. Eight targeted tests passed locally. No new network calls, paid service, D1 change or runtime route is required.

## Native EDGE paid-sale collection — 2026-11-18

The scheduled collector can discover public lot links via Gemini Google Search and confirm paid EUR lots directly on the source page for five exact French variants. A unique D1 claim bounds discovery to one request per UTC day. Paid lots are immutable and keyed by source lot ID. The Radar reads the same D1 evidence and passes it to the existing calculations. Two integration tests passed locally against SQLite with simulated source responses, including retry deduplication and an updated resale quote. The previous conversation-based scan has been paused. No remote Gemini call, D1 schema application or activation of this collection feature was performed for this change. See ADR 008 for activation requirements.

The collector now rotates across cards, boosters, sealed boxes and releases without specifying card names in the discovery prompt. Generic verified graded/sealed sales can feed the Radar's 30-day median and volume comparison; Leboncoin/Vinted and Pokémon publication links are unverified leads. Event-to-variant matching and comparisons of past catalysts are still pending. Four targeted tests passed locally, including the coverage rotation, SQLite integration and variant-level trend calculation. Remote collection still requires activation.

The trend analysis checks up to 360 days for earlier instances of the same variant and directional signal. Nonoverlapping sequences measure whether the following period continued the move. The four targeted tests pass with the backcheck enabled. This calculation does not attribute market movements to events.

Daily collection now uses one Gemini request per UTC day for all four families, with up to eight retained links per family. Missing response sections yield a partial run if other sections are present. A quota or billing response ends the cycle without fallback. The SQLite integration test covers the grouped request, a partial run, quota cutoff and concurrent retries. Activation requires a free-tier Gemini project without billing, and the Cloudflare Free plan. No live scans were run for this change.

## Free TCGdex and Cardmarket collection — 2026-11-18

`scripts/cardmarket_history.py` ingests the public Cardmarket Pokémon catalogues and daily guide into a local SQLite history. The official guide dated 2026-11-17 yielded 67,459 cards, 732 boosters, 975 box sets, 517 displays, 402 blisters and 167 ETBs with usable values, plus other sealed formats. An identical import inserted no second snapshot. Two Python regression tests and local validation of the frontend price-window parser passed. The Radar displays the overlapping 7/30-day Cardmarket averages from its existing TCGdex price snapshot, with the source date and a staleness label. The separate full-catalogue importer has no deployed schedule or persistent cloud destination yet. No Gemini key or billing was enabled.

## Market language evidence — 2026-11-18

The Explorer supports Italian catalogue searches and detail pages. The catalogue quote exposes `marketLanguage: null` because the provider's aggregates do not identify an exemplar language. A live comparison of TCGdex FR and IT for base1-4 returned the same Cardmarket product ID and the same low, 7-day and 30-day prices. Documented sales on catalogue detail require an exact reference and exact language in the paid-sale key; an absent language dataset stays empty. The Radar shows the full variant when rendering tracked sale trends. No D1 schema changes or new provider calls were required.

## Manual Cardmarket offers by language

Catalogue detail accepts manual asking-price observations with a Cardmarket singles link, stated condition, timestamp and explicit confirmation of the reference and offer language. The browser keeps up to 20 records per card and language. This is a listing observation entered by the user. No remote scraper, completed-sale inference, account access or cloud persistence was added.

## Public Graded Card Center discovery
The collector schedules public-auction discovery without a paid model. It samples up to four new lot links and visits up to six due lots per UTC day. The D1 queue preserves pending lots for up to 28 days; only an explicitly paid, validated lot enters the existing immutable sales table. The source HTML check found 24 lot links and extracted a known paid FR PCA 9 Noctali VMAX sale at EUR 1,750 on 2026-05-27. The active-to-paid queue transition was tested in SQLite with fixtures. Deployment of the scheduled collector and application of the additive D1 table remain separate live steps.
