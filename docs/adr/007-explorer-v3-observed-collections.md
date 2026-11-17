# ADR 007 — Explorer V3: observed collection browsing

Status: Implemented on development branch; CI and mobile rendering pending.

## Context
The user validated real TCGdex images on iPhone and requested visible progression toward the 18 reference screenshots: collection tiles, browsing and sealed products. The current integrity-checked market snapshot has only two observed Pokémon cards and no verified sealed-product records.

## Options
A. Build category tabs, collection tiles and sorting over the existing observed snapshot, with an explicit empty sealed-products state.
B. Populate a complete-looking catalogue using fabricated items and prices.
C. Integrate a new external catalogue immediately without a provenance/licensing/data contract.

## Decision
A. No new network requests, external data providers, persistence, or paid model calls. The category distinction is a UI contract, not evidence of sealed-product ingestion. Collection thumbnails reuse observed card illustrations and do not claim to be official set logos.

## Follow-up
Implement a separately verified catalogue feed (including sealed products), preserving a strict separation between catalogue metadata, live asking prices and completed sales. Extend AI contextual analysis only after controlled evidence and budget contracts.

## Reversibility
Restore previous ExplorerGrid and remove V3-specific CSS. No migrations.
