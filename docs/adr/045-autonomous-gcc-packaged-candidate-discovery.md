# ADR 045 — Autonomous catalog candidate backlog from observed GCC paid-sale keys

Date: 2026-11-20
Status: draft implementation; no deployment, remote D1 mutation or OAuth activation.

## Problem
The verified packaged-product catalog in ADR 044 deliberately has zero
entries. This prevented false comparables but also left no autonomous
mechanism to identify which ETB, UPC, display or named coffret references
should be researched for eventual inclusion.

## Decision
A new pure collector module `leboncoin-product-candidates.mjs` inspects
bounded actual `paid_market_sales` rows already read by the operator-only
private offers view. It accepts only:
- existing version-1 eight-part packaged variant keys with valid type,
  set, product, language, edition, unit count and sealed marker;
- canonical Graded Card Center completed-sale lot links, distinct lot IDs,
  positive integer sale prices, and nonfuture valid sale dates within
  the allowed evidence horizon;
- at most 1,000 source rows; oversized or missing results fail closed.

It produces a deterministic, ranked backlog with `CANDIDATE_UNVERIFIED`
and explicit missing proofs: manufacturer reference, packaging and
locale verification, reviewed product identifiers and listing identity.
It ranks by number of distinct dated paid lots and recency. Candidates
are not automatically placed in the reviewed catalog, converted into
completed market evidence, or used to justify comparing an emailed ad.
No official product URL, product fact, sales price, scarcity claim or
buy recommendation is fabricated.

The private HTML view now displays the candidate backlog only after
the same signed Cloudflare Access authentication as the read-only
offers history. If the paid-sale ledger is absent or truncated, the
view states source unavailability rather than falsely reporting a
verified empty market. No user input form is provided.

## Verification
Offline Node regression covers valid real-shaped GCC paid rows,
duplicate-lot suppression, forged source URLs, invalid keys, wrong or
future dates, capped/truncated source results and stable sorting.
Private HTML tests enforce the `CANDIDAT · NON VÉRIFIÉ` status
and the distinct missing-ledger state.

## Outstanding requirements
The backlog does NOT itself independently verify manufacturer
references or populate the production catalog. A separate provenance-
checked autonomous discovery and audit path is needed before any
candidate can become `VERIFIED`, and even then paid-sale comparables
still require at least three distinct transactions in 90 days.
Dedicated EDGE Microsoft OAuth, remote Cloudflare Access, D1 and
scheduled collection remain unactivated.
