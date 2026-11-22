# ADR 043 — Conservative sealed product comparables in Leboncoin radar

Date: 2026-11-20
Status: draft implementation only, without remote D1 or Microsoft authorization.

## Motivation
The GCC paid-sale variant model already recognizes certain sealed
`booster` and `coffret` records, but the Leboncoin matcher previously
supported only fully described graded individual cards. This iteration
adds product-type-aware comparisons without pretending that a loosely
described sealed box or bundle is identical to a single booster.

## Matching contract
The sales ledger variant must match the existing exact seven-part
`booster|coffret:pokemon:<set>:<product-name>:<language>:<printing>:scelle`
schema. The email-derived ad title must explicitly state:
- the same product series and identifying name;
- the same language and printing/edition;
- a sealed/unopened condition; and
- the exact packaging type: for boosters, evidence of a single unit
  (e.g. `1 booster`, `booster unitaire`); for coffrets, an explicit
  `coffret` label.

Reject mixed lots, multi-booster displays and bundle packaging, missing
edition/language/sealed claims, invalid schemas and ambiguous matches.
No automatic equivalence between booster, ETB, display, tin, UPC and
coffret; no raw/graded equivalence.

As for graded individual cards, the comparison uses only records
from `paid_market_sales` with exact canonical GCC source URLs, at
least three distinct paid sales in the previous 90 days, and a bounded
read-only D1 query. The comparison shows gross median, lowest gross
sale and the gross difference from the emailed asking price, never
an expected net return or a BUY command.

## Limitations
A seller's text is a claim, not verified packaging, authenticity,
sealed condition or present availability. This deliberately strict
first implementation will miss many true matches, especially listings
without explicit language/edition details. Reliable broad support for
ETB, UPC, displays and region-specific products needs a versioned
product identity catalog or additional verified structured attributes,
not relaxed string matching.

The separate Outlook collector Worker remains off and not deployed.
No mailbox data is ingested into D1 by this PR; `main` stays unchanged.

## Tests
Offline tests cover complete unit-booster and named-coffret matches,
insufficient paid sales, incomplete descriptions, displays/lots,
ambiguous language variants and continued graded-card matching.
The full Cloudflare build and Outlook test workflow are checked per
commit.
