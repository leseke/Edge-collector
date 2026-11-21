# ADR 044 — Versioned, review-gated packaged product identities

Date: 2026-11-20
Status: draft PR only, no deployed or reviewed product data.

## Goal
Extend EDGE's comparison infrastructure beyond graded cards, sealed
single boosters and named coffrets to **ETB, UPC, display and named
coffret packaging**, without relying on a vague seller title or
mistaking one 36-booster display for a single booster.

## Catalog design
`src/leboncoin-product-identities.mjs` implements an immutable
schema-versioned catalog and pure matching function. Version 1 records:
- `variantKey`:
  `etb|upc|display|coffret:pokemon:<series>:<product>:<language>:<printing>:u<unit-count>:scelle`
- `reviewStatus=VERIFIED`, `version=1`, `verifiedOn`
- a canonical HTTPS `officialSource` from an allowlisted official
  Pokémon domain, without embedded credentials/parameters
- at least two independently reviewed exact `identifiers` that must
  both appear in the listing's title.

The listing must explicitly state full series, product, language,
printing/edition, sealed condition and packaging type; unit count
must agree. Exclude cross-category packaging and generic multi-lots.
Unverified records, invalid schema, ambiguous matches and missing
attributes produce **no comparable**. This is a deliberately strict
read-only matching gate and not a fraud-detection guarantee.

## Production population policy
The code starts with **zero production reviewed records**. Synthetic
examples containing official-domain-shaped URLs are ONLY test fixtures;
they are not evidence that those particular products exist or have
ever been reviewed. Actual production records must be verified
against authoritative original source material and the exact
`paid_market_sales.variant_key` identity before inclusion.
No manual end-user form or confirmation flow is introduced.

The matcher may return a catalog product only when the corresponding
exact variant key exists among recorded paid GCC sales. The
pre-existing at-least-three-distinct-paid-sales-in-90-days rule then
applies. Product identification alone is NEVER a signal of profitable
resale, live availability or buy readiness.

## Limitations
- Different regional configurations, languages, Pokémon Center
  variants, print runs and bundle composition require their own
  reviewed identities.
- The current official-domain shape check is necessary, not
  a verification that the linked official page actually describes
  the product. Review and source audit remain separate obligations.
- The catalog is static at build time and will later need curated
  source ingestion, change history and review workflow; no user
  input is required.
- Live independent Microsoft OAuth, Cloudflare Access provisioning,
  remote D1 migration and deployment remain outside this PR.

## Regression tests
A synthetic reviewed record checks full-key ETB matching, three
independent canonical paid GCC lots, and refusal of incomplete,
unreviewed, ambiguous, off-domain or wrong-schema products. Additional
synthetic tests cover UPC, display and boxed products, sealed state
and package unit counts. Outlook CI and full Cloudflare build run
without any mailbox or remote database mutation.
