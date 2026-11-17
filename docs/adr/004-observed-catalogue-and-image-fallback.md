# ADR 004 — Observed catalogue and image failure fallback

Status: Implemented on development branch; CI and mobile verification pending.

## Context
Mobile screenshot of the first investor home showed a broken product image and only two observed cards. The user requests visible progress toward collection exploration without invented market data.

## Options
A. Reuse verified snapshot cards, provide search/set filters, and handle image load failures in the browser.
B. Integrate a third-party full catalogue immediately, without establishing licensing, API reliability, provenance or scope.
C. Hardcode products and images to simulate a full collection.

## Decision
Choose A as a reversible, honest first Explorer. No new data source, API key, AI call, database write or deployment is authorized by this ADR.

## Consequences
The Explorer covers only the currently observed cards. An image failure displays a deliberate fallback instead of a browser broken-image icon. This does not establish why the original image URL failed; source URL diagnostics and a licensed catalogue integration remain separate work. No sealed products, card scanning, full catalogue, or contextual AI assistant is claimed.

## Reversibility
Remove /explorer route and AssetImage component; restore original dashboard image markup. No persistent data changes.
