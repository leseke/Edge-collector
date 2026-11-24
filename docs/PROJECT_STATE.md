# EDGE — canonical handoff

Updated 2026-11-24. Development branch: edge/tcg-multi-agent-orchestration-001. PR #5 (draft; recheck live status). Main must remain untouched.

## Verified baseline
- Next.js dashboard reads latest.json from edge/commercial-history and validates report and raw payload hashes. Current UI is Pokémon-card observations, not a comprehensive TCG catalog.
- Card evidence dossier, JSON corpus export and same-tab local inquiry handoff exist. Local companion is experimental and requires explicit local setup.
- TypeScript corpus generator and Python validator contract test exist; CI for e374e033dd391323c43923038d5f170769c20647 succeeded (Next.js #224, offline #301). Whether Node-dependent test was skipped needs job-log confirmation.
- app/lib/tcg-history.ts and tests/tcg_history_contract.mjs exist. Historical index is not yet confirmed wired into the dashboard. Standard history index paths tested returned 404; actual publisher layout needs inspection.
- Latest inspected commercial capture: 45179610868-1, 2026-11-23, PARTIAL. Do not treat as current without refreshing.
- No full audit or production readiness claim. Active offers, completed sales coverage, autonomous discovery, portfolio and full UI integration need verification.

## Next executable delivery
Market Explorer: connect actual active offers and completed sales to product detail, inspect existing collectors and routes first. Verify the new explorer in browser and wire its Node contract into CI if not already executed. Inspect historical publisher to connect real historical data rather than invent an index.

## Handoff discipline
Each session records actual delivered outcomes, code commit IDs, validation evidence, pending tests, known blockers and next executable task here. Reconcile against current HEAD, including automation commits. No conversation memory is required.

## Delivery — Market Explorer search
- Connected latest verified snapshot to interactive search (accent insensitive, name/number/rarity/series), series filter, currency-grouped indicative price sorting, reset and progressive display. Existing evidence details retained. Explicit partial catalog and unknown offer/sale coverage.
- Code commits: 35a75d2a7ef63a622fca0f7d7a3a21840bf90ac0, 9061ce8f151670e5e0818ddcbaf2649cb6eb3665, bd85cfe90327bed838c64f1159fdfdcf0f88bd9d, b980d48f1d2b64c2cfaf7bdbc38dc50133c7d044, 864b9137e27068757328bc8cd4b810cd6988f209.
- Node contract added; execution, final CI and browser preview not yet confirmed. PR #5 confirmed open draft before changes. No production deployment.

## Delivery — commercial observations
- Data adapter exposes exact product-ID matched observations, source URL (HTTPS only), price, currency, date, availability and collection status. Product cards separate asking prices, declared sales and indicative aggregates. Commits bc87c2af0552d44dae62a15e28bb6f7346be1b62 and 66a6e0b5ce9a82ee2410458d2eeae7039354e550.
- Actual capture 45380419399-1 (2026-11-24): 16 observations across categories, no declared completed sales. Auction coverage remains unknown. No independent transaction verification.
- CI at interface commit: [{"name":"Next.js build","status":"completed","conclusion":"success","id":45402073665},{"name":"EDGE MRI offline tests","status":"completed","conclusion":"success","id":45402073828}]. Browser not verified.
- Next: inspect existing listing collectors and connect real TCG listings and auctions; add production-code contract tests for classification and unknown coverage. No production deployment.
