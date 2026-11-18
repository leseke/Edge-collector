# 014. GCC public catalogue in the Radar

## Context
The original Radar sampled the first listing grids and displayed a separate, curated history of paid sales. The GCC public browsing interface has open-auction, fixed-price and closed-lot views, and returns an opaque cursor for continuation.

## Options
Keep a static sample, crawl and persist the entire catalogue, or paginate the public browsing feed on demand.

## Decision
Paginate the public Pokémon feed on demand using the same upstream cursor as the GCC browsing interface. Validate each response and retain only public lot information. Group closed results by set on the current page and offer an upstream set filter that applies across all pages. Prepopulate the filter with up to 200 series and accept other exact labels. Cache each page briefly and keep original source links.

## Consequences
The user can navigate all listings exposed in the public feed without bulk requests. The catalogue can change between pages. Closed and waiting-for-payment lots are never added to verified paid sales. The change is reversible without database changes.
