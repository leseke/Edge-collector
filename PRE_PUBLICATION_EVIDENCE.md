# EDGE — Audit des preuves avant publication

Implemented 2026-11-01. Reaction windows keep their existing 24/72/168 h horizons and 6 h outcome tolerance. This change adds an explicit, source-specific baseline audit; it does not fabricate missing history.

- A baseline must be strictly earlier than the declared publication time and no more than 24 h old. A simultaneous quote is excluded. The 24 h boundary is included.
- Status AVAILABLE means only that a descriptive asking-price baseline exists. It is neither a forecast nor evidence of causality.
- STALE_PRIOR_CAPTURE preserves the last older observation for diagnosis but excludes it from reaction measurements.
- NO_PRIOR_CAPTURE means there is no valid archived quote strictly earlier than the publication. Later collection cannot repair this gap retroactively.
- The selected evidence retains its observation ID, timestamp, price, currency, declared availability and body SHA-256. First capture time and its signed offset from the publication are retained too.
- Invalid dates, missing body proofs and nonfinite/nonpositive prices cannot serve as reaction quotes.
- Dossiers attach measurements using the full observation/source/seller/product/currency identity. Reused identifiers from another seller cannot enter a case.
- UI details show the diagnostic for each publication/source measurement. Older archived captures without the added fields remain readable.

## Realized sales: access review, 2026-11-01

No realized-sales connector is claimed operational by this change.

1. eBay's official marketplace support page explicitly says Marketplace Insights is restricted and not open to new users. Browse listings must not be relabelled as completed transactions. Documentation: https://developer.ebay.com/api-docs/buy/ref-marketplace-supported.html and https://developer.ebay.com/develop/get-started/get-started-on-a-buying-application .
2. BrickLink documents guide_type=sold for Last 6 Months Sales and guide_type=stock for current inventory. Requests require OAuth credentials; the documented token setup also registers client IP addresses. This is a candidate for an authenticated integration, not an active data source in this repository. Documentation: https://static.bricklink.com/alpha/default/api_wiki.html .
3. A six-month aggregate can establish historical sales statistics but cannot alone measure a reaction in the 24 h after one publication. Period, product, condition, geography and currency must remain explicit. Overlapping rolling windows cannot be counted as independent transactions.

## Next acceptance criteria

Maintain price/stock captures for already monitored products so a future publication can have a genuine prior baseline. Verify a usable authorized sales access path before implementing a connector. Preserve the distinction between retail asking prices, historical sales aggregates and individually dated completed transactions. No account creation, paid subscription or token provisioning was performed for this review.
