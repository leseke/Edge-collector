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

## Future-event preparation (2026-11-01)

Every collector run now stores `collection_coverage.json.event_preparation`, alongside the existing incident audit. It covers the asking-price product/source pairs present in the current run, not the entire discovery universe. It does not increase request volume or change the source limit.

For each source it records the latest valid proof and its 24 h expiry, total distinct successful capture count, distinct captures in the preceding 24 h, maximum gap in that recent series, and the current attempt status. Exact source URL, seller, product and EUR currency must match. Invalid/future/unproven observations are excluded. Replayed timestamps are counted once; contradictory price/stock values at one timestamp are excluded altogether. Two pages from one seller are never two independent sellers.

`RECENT_SERIES` means multiple recent observations without an observed interval over six hours. `GAPPED_RECENT_SERIES` preserves the gap; `SINGLE_RECENT_CAPTURE` is not presented as a price trajectory. `COLLECTION_INTERRUPTED` preserves an earlier valid proof while making the latest source failure explicit. `STALE_HISTORY` and `NO_VALID_CAPTURE` cannot provide a recent potential baseline.

The public interface recalculates whether the evidence has expired when rendering. Counts describe potential comparison evidence for an event occurring now; they do not predict an event, confirm a reaction, or qualify an investment. A historical gap before a past publication remains unfilled.

## BrickLink integration prerequisites

There is no BrickLink authentication or sales request in the collector workflow. The remaining work requires an authorized account/access configuration and a suitable registered egress IP as described by BrickLink's API documentation. No credentials are requested or stored by the public dashboard. A GitHub-hosted runner's changing egress must not be silently assumed to satisfy a registered-IP requirement.

An eventual read-only connector should request `guide_type=sold`, preserve item condition, country/region, requested currency and six-month period, archive the original response/hash, and retain errors as unavailable data. `guide_type=stock` must remain asking-price inventory. Six-month rolling aggregates must remain separate from dated individual transactions and from 24/72/168 h event outcomes. No consumer account creation, paid service or API activation was performed here.
