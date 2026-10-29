# Commercial history pilot

This pilot extends persistent history to two French retail pages for LEGO 10365.
It does not modify the existing collector, radar, TCGdex history, capital or Telegram.
The scheduled workflow runs every six hours at minute 37 UTC; GitHub can delay runs.

Each run appends a new folder to `edge/commercial-history`: raw HTML where retrieved,
SHA-256 manifest, report and events. Failed observations are archived too. Status is
OK, PARTIAL or FAILED according to offer extraction, not merely HTTP success.

Extraction requires exactly one JSON-LD Product matching the SKU and one EUR Offer.
Ambiguous offers, aggregate prices, identity mismatches and inaccessible pages fail
closed. UNKNOWN availability never means out of stock. No bypass or paid API is used.
Seller identity is the configured retail site; this pilot must not be extended to
marketplace listings without extracting and matching the actual seller.

Prices are asking prices excluding unknown delivery charges, never completed sales.
A first capture is a baseline. Later successful observations for the same source and
product generate PRICE_CHANGE, AVAILABILITY_CHANGE or RESTOCK_OBSERVED transitions.
The last successful observation supplies the previous state; gaps remain visible
through the time window. Events represent a change observed within that window,
not an exact event timestamp, a proven cause, a confirmed promotion or a buy signal.

Remaining MRI work: announcement/reprint/withdrawal sources, cross-seller coverage,
completed-sale evidence and event-centred reaction windows. This pilot cannot yet
measure resale liquidity or demonstrate a predictive advantage before consensus.

## Live validation
The first retail run (40969904702) archived FAILED evidence: LEGO HTTP 403,
La Grande Recre redirected to a verification page. Neither yielded an offer.
Two TCGdex card endpoints are therefore added as an explicitly separate price
series: Cardmarket indicative low, not executable offers, not sealed products,
not verified French-language transactions. Availability remains UNKNOWN. The
upstream update timestamp and entire pricing payload are retained. Changes emit
INDICATIVE_PRICE_CHANGE, distinct from retail PRICE_CHANGE. Retail targets remain
visible as failures; they are not silently replaced or counted as successful.
