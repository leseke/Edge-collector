# ADR 041 — Email-only price-drop and repeated-offer investigation cues

Date: 2026-11-20
Status: isolated PR, not deployed.

## Purpose
The protected Leboncoin offers view already deduplicates listing IDs and
retains first and latest email asking-price observations. This change
makes the most meaningful observations easier to find without inferring
actual market value from those excerpts.

## Decision
Use a deterministic triage helper, `leboncoin-lead-triage.mjs`, to
organize up to 50 most recently observed distinct D1 listing IDs.

- PRICE_DROP: the listing appeared in at least two distinct emails; both
  the first and last requested prices are nonnegative integers; the first
  price is nonzero; the last requested price is at least **5%** and **€5**
  below the earliest; the **latest email observation** is at most 48
  hours old. This is a *lead to investigate*, not a BUY recommendation.
- REPEATED: at least two distinct email appearances, latest observation
  within 48 hours, but no qualifying price drop.
- OBSERVED: everything else, including missing prices, one-off sightings
  and older data.

Display qualifying price-drop leads first, then recurring alerts, then
other observations. Sort qualifying drops by larger relative asking-price
decrease and break ties by observation recency. No new data collection,
new AI inference or action button is introduced.

## Explicit limitations
- The 48-hour cutoff describes the freshness of the LAST email, not the
  elapsed time between the first and last asking prices. A historical
  price change can be flagged when seen again recently.
- A lower email asking price is neither evidence of a paid sale nor
  proof of available stock, item condition, grading, seller legitimacy
  or undervaluation against comparable sales.
- No investment percentage return, expected ROI, confirmed liquidity,
  budget constraint or automatic purchase is calculated here.
- Candidate ranking is limited to the latest 50 unique D1 listing IDs
  chosen by the query; it is not a comprehensive ranking of all
  Leboncoin listings or search results.
- D1 observations are append-only, and raw mailbox data/credentials
  are never exported into the repository.

## Verification
Offline tests cover a 13% recent asking-price decrease, minimum
threshold rejection, increases, missing/zero prices, one-off reports,
stale/future timestamps, stable sorting and avoiding bought/sold claims.
The existing signed-Access private view remains disabled without
separate Outlook Worker flags. The full Cloudflare build and Outlook
CI must both pass.
