# ADR 003 — Product-first investor home with progressive disclosure

Status: Implemented on development branch; deployment and mobile rendering require separate verification.

## Context
The current home prioritizes collection counters and educational text. User-provided mobile references favor recognizable products, strong image/price hierarchy, and clear navigation. Existing public market snapshots contain only limited observed TCG cards; there is no authenticated interactive AI gateway.

## Options
A. Replace home with a product-first grid, move methodology into native disclosure, and show AI as not yet active.
B. Keep operational counters at the top and add color styling.
C. Invent demo products and investment scores to populate a richer dashboard.

## Decision
A. Reuse existing `getTcgMarketSnapshot()` and `TcgCard` without adding API calls, purchases, paid AI, or synthetic market content.

## Rationale
Immediately visible product cards make the UI more useful without overstating evidence. Native `details` keeps source and caveat information accessible. Explicitly inactive AI avoids deceptive readiness claims.

## Consequences
The home remains a read-only market view. It does not yet have product detail routes, a full catalogue, reliable sales, investment rankings, or an assistant. Remote product images are allowed only through the existing TCGdex URL allowlist. Current observations are not presented as investment recommendations.

## Reversibility
Restore the prior dashboard component and remove appended `edge-` styles and associated tests. No data schema change or backend side effects.
