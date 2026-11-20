# ADR 042 — Strict matching of Outlook offers to paid GCC comparables

Date: 2026-11-20
Status: draft-only; no live Outlook, remote D1 or production deployment.

## Objective
Connect Leboncoin asking-price signals with **actual recorded paid GCC
sales** without inventing identity matches or claiming that a listed
item is equivalent to a paid graded card.

## Rule
A read-only matcher recognizes only the full structured
`carte:pokemon:<set>:<number>:<name>:<lang>:<printing>:<grader>:<score>`
paid-sale identity already stored in the GCC ledger. The ad's title
must explicitly contain ALL matching normalized attributes: expansion,
card number, card name, language, edition/printing and grader/score.
There is no fuzzy guess, equivalence between raw and graded cards,
auto-assumed language, grade or edition, or fallback match on a
character's name. Ambiguous matches fail closed.

For an exact unique variant, only authorized `paid_market_sales` records
with canonical GCC source links, positive integer paid prices,
valid sale dates within the most recent 90 days and distinct lot IDs
qualify. At least **three distinct transactions** are needed to show
the gross EUR median and the lowest observed gross sale. When an asking price is known, the view also shows the **gross difference** versus that lowest paid sale, without accounting for acquisition fees, delivery, resale costs or item condition: it is NOT net profit. Two sales
or an incomplete variant are explicitly insufficient.

The view performs a capped, read-only lookup of the existing
`paid_market_sales` table (at most 1,000 rows in the 90-day window).
If the table or its D1 binding is unavailable, a query fails, or the
window exceeds the bound, **no comparison** is shown. Imported mail
observations are never converted into paid-sale records.

## UI
- `COMPARABLE`: show count of documented paid GCC sales, the
  90-day gross median and observed minimum, plus a notice that
  physical product identity remains unverified.
- Other states: clearly state no reliably matched paid-sale comparison.
- Never imply an automatic BUY decision, guarantee, net ROI, current
  listing availability or resale profit. Transport, acquisition and
  resale fees remain unknown.
- The radar's manual Leboncoin URL form stays removed.

## Limits and next step
This first matcher intentionally supports only full nine-part
`carte:pokemon` variant keys and richly described listings. Older
short-key archive formats, sealed boxes, booster packs or missing
attributes cannot be declared exact comparisons. This is restrictive
by design and may produce many NO_VERIFIED_VARIANT results. Broader
product matching requires a reviewed identity catalog and distinct
variant/condition evidence, NOT a relaxing of matching thresholds.

This does NOT authorize provisioning, deploying, app consent, remote
D1 mutation or scheduling. EDGE's independent Microsoft Entra OAuth
and Cloudflare Access configuration remain prerequisites for live
mailbox collection.

## Tests
Offline tests cover complete-identity matching, missing series,
number, language, edition or grading, ambiguous titles, duplicate
lots, forged/noncanonical GCC URLs, too few paid sales,
future/stale sales, and successful median/minimum display.
