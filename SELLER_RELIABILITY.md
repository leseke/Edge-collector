# EDGE — Seller reliability gate

Price extraction and merchant reliability are independent. An identified retailer page can supply a correctly observed price/stock while the seller remains unverified. Unknown reliability is not evidence that the seller is fraudulent.

## Decision consequences

- Observations from unverified sellers remain in price history, product discovery and descriptive market comparisons. No capital filter is introduced.
- They cannot set the seller-qualified economic comparison floor or spread, and cannot clear the purchase-preparation gate. An attractive price never compensates for a missing merchant review.
- Public labels say prix observé rather than offre vérifiée. Every unverified or expired seller has an explicit Achat non validé message. Descriptive price differences are labelled as observations without purchase validation.
- Per-product MRI cases and individual candidate assessments persist the blocked gate and missing seller-reliability evidence. Source observations keep their dates and proofs.
- Research observations and descriptive event/stock estimates remain distinct from financial recommendations. No research probability grants seller approval or purchase authorization.
- Even a verified seller does not create a buy signal: stock, delivered cost, actual resale evidence, liquidity, margin and the existing authorization requirements still need evaluation. The gate only establishes eligibility for further analysis, never automatic purchasing.

## Review evidence

Only seller_reviews.json is authoritative for this gate; page metadata, extraction success, existing established-retailer labels, source booleans and manufacturer announcements cannot grant seller verification. The registry currently contains no completed audits. Therefore no real seller is promoted to VERIFIED by this change.

One active review must match both seller name and HTTPS site origin. It must record a non-future review date, an expiry no more than thirty days after that date, and PASS evidence for legal identity, official domain, terms/returns and recent reputation. Each check requires a public HTTPS evidence URL and its archived-content SHA-256. Missing, incomplete, mismatched, duplicate or future reviews do not clear the gate; expired reviews become EXPIRED. These are documented audit decisions, not an automatically inferred trust score. An administrator must actually verify and archive the referenced evidence before entering an approved review.

The backend computes the decision metadata from this registry, ignoring source-provided flags. The browser also checks review scope, dates and expiry when rendering a qualified floor. Legacy captures without reliability metadata default to unverified. Original archived observations are not rewritten.

## Validation

Tests cover self-asserted trust flags, ordinary retailer labels, missing evidence, domain mismatches, duplicate audits, review age/expiry, unavailable or failed offers, assessment persistence, and a cheaper unverified seller being excluded from the economic floor while retained in descriptive prices. Seller approval by itself never produces BUY or purchase authorization.

Next audit: check BRICKshop's legal identity, official domain, current terms/returns, independent reputation evidence and France-specific delivery before considering an eligible purchase offer. Keep it a market observation while these checks remain incomplete.
