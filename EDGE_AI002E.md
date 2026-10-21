# EDGE AI-002E — Transaction-source feasibility and supervised import

2026-10-21. This lot does **not** collect real transactions. It validates access feasibility and implements an **offline candidate import**. No API keys, no network calls, no paid services, no deployment.

## Access research (official provider docs)
- eBay Marketplace Insights `item_sales/search`: limited release, select approved developers; 90-day history. https://www.edp.ebay.com/api-docs/buy/marketplace-insights/static/overview.html
- Cardmarket API: application access restricted to approved professional sellers. https://apiv2.cardmarket.com/ws/documentation/API%3AAuth_Overview
- TCGplayer API: no new developer access. https://docs.tcgplayer.com/docs/getting-started

Do not infer that publicly accessible sold-listing pages grant scraping or redistribution rights. Third-party API claims require separate licensing and provenance assessment.

## Implemented
`intelligence.transaction_ingest` validates manual or licensed-export candidate records and stores only `unverified` candidates, never a verified sale or price-history point. Candidate URL and evidence label are self-reported: URL existence and proof authenticity are NOT checked. No EDGE policy decision fields are accepted. Deduplication uses SHA-256 of normalized input. Validation happens before append.

## Explicit limitations
- Not a marketplace API integration.
- Candidate entries cannot be used to compute confirmed-sale medians, liquidity or trading ROI.
- No live price data, platform transaction verification or license acceptance.
- Journal is append-only for sequential use only; not safe for concurrent writers, and no signature or integrity anchor.
- Date/time and currency format checked, not product equivalence or currency validity.

## Validation
- `python -m unittest tests.test_ai002e -v`: 6 passed.
- `python -m unittest tests.test_ai002c tests.test_ai002d tests.test_ai002e -q`: 34 passed.
- Full repository suite not validated by this delivery.

## Next gate
Before external ingestion: obtain actual provider authorization/license; map provider-specific sold-status semantics; validate URLs and records; agree retention and redistribution terms; implement permissions and periodic spend cap; test full offline regression; require human approval for provider activation.
