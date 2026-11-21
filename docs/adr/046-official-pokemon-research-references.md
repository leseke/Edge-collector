# ADR 046 — Official Pokémon research references without false product verification

Date: 2026-11-20
Status: draft; source-linked, non-production, no mailbox/remote D1 changes.

## New evidence
The Pokémon Company's public product gallery documents:
- Scarlet & Violet—Prismatic Evolutions Elite Trainer Box (US product
  page; January 17, 2025);
- Celebrations Ultra-Premium Collection (US product page);
- Mega Charizard X ex Ultra-Premium Collection (US product page;
  November 14, 2025).

These are **official manufacturer research pages**, not verified
equivalences to any seller's exact edition or to a GCC paid lot.
The entries contain only published titles, source URLs and dates where
explicitly available. No fabricated EAN, SKU, language equivalence,
package contents or sale prices are added.

## Implementation
`leboncoin-official-product-research.mjs` contains a curated, immutable
initial list of these official links and a conservative association
function. The private operator-only view may suggest a research link
only when the unverified GCC candidate's packaging family, series and
English/US locale align with the source entry. Other languages,
series and product families remain unmatched.

The returned status is `RESEARCH_LEAD_ONLY` and NEVER `VERIFIED`.
The module does not mutate the vetted product identity catalog, does
not supply missing EAN/UPC or verified listing attributes, and does not
unlock paid-sales comparability. Only a verified exact product identity
record can do that, under the existing stricter controls.

## Boundaries
This is an initial source-provenance step, **not a general-purpose
live search crawler**. A future safe official-source collector must
independently validate product title, exact package identity and
regional specification before promoting any candidate. Product-gallery
pages may require server-side dynamic content; URL existence alone
does not prove package details. No user input is needed.
No Entra OAuth grant, deployment, cron or remote D1 mutation performed.

## Offline regression
Tests verify official URL provenance, absence of promoted variants,
English-only association, refusal of mismatched series/packaging and
rejection of off-domain injected URLs.
