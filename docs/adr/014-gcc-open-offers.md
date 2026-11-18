# 014. Open offers in the Radar

## Context
The paid-sale history only retains a subset of exact verified transactions. Public GCC pages also list open auctions and fixed-price items.

## Options
Expose source links only, add a read of the public grids, or persist a separate offer history.

## Decision
Read the two public Pokémon-filtered listing grids in parallel and show up to eight open Pokémon entries per group. Require a matching action and a euro price and exclude expired auctions. Bound the request and HTML size, cache only parsed public snapshots for 120 seconds in the preview Worker and keep links when the source is unavailable.

## Consequences
An active offer is separate from the immutable paid-sale dataset. A sample cannot establish full inventory or a sale. Prices are observed values with a timestamp. The view can be removed without modifying collection history or schema.
