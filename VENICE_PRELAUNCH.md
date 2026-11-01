# EDGE — 11388 pre-release observation

## Source and scope

A direct BRICKshop product page is configured for LEGO 11388:
https://www.brickshop.eu/lego/lego-icons/lego-11388-venetian-neighbourhood.html

The public page was read on 2026-11-01. It displays EUR 599.99 and COMING SOON, with a retailer-declared availability date of 4 November 2026. This is an observed retailer asking price for an unavailable product, not an executable checkout, a completed transaction, a French delivered price, or a verified resale opportunity. Retailer trust and France delivery have not been independently audited. No purchasing action is performed.

The manufacturer press release separately announces general release on 4 November, early access on 1 November and an associated conditional 40898 gift. This observation is after the first announcement and early-access start, but before general release; it cannot be treated as evidence predating the original announcement. No launch hour is invented.

## Extraction guards

The new adapter requires one identified main product table. Its barcode, microdata GTIN, exact SKU, LEGO brand and visible heading must agree. There must be one scoped EUR Offer whose URL matches the configured page. The visible selected EUR price must equal the microdata price. Approximate currency conversion attributes and recommendation-card prices are ignored.

The visible Online status is read separately from the physical store status. COMING SOON with machine OutOfStock becomes COMING_SOON, not a reported stockout. An eventual in-stock state must be confirmed by both machine metadata and visible online text. Missing, ambiguous or contradictory fields fail closed and retain the original response as evidence.

COMING_SOON contributes a verified displayed price but never an available purchase floor, in-stock count, observed stockout or computed resale margin. The user sees À venir and Livraison en France non confirmée.

## Event dossier

A case with one currently verified seller is permitted only when a currently rechecked manufacturer source supports an announced general-release date. The date remains day-granular, distinct from publication timestamps. It is shown as an announced event with an explicit unestablished market effect. Existing multiple-seller counts retain their original meaning.

The new target uses one source slot. Eleven base targets leave capacity for five research targets within the existing total limit of sixteen. There is no paid service, new message destination or capital filter.

Next evidence: verify the first immutable production capture, preserve subsequent pre-release observations, and compare later stock/price changes with their actual dates. Neither a date-only event nor an unavailable displayed price supports a causal reaction, liquidity estimate or buy signal.
