# ADR 006 — Read-only MRI evidence and exact product linkage

Status: Implemented on development branch; CI and mobile rendering not yet verified.

## Context
The integrity-checked MRI snapshot contains cases including LEGO, but no `pokemon_card_` case in the snapshot inspected on 2026-11-17. Showing invented theses on the two observed Pokémon cards would mislead.

## Options
A. Expose bounded publication metadata from the already SHA-verified MRI snapshot, render read-only evidence cards in Radar, and link product details only by exact `product_id`.
B. Generate synthetic analyses for every observed product.
C. Enable paid DeepSeek automatically to fill missing cases.

## Decision
A. Keep actual case reaction status and financial decision unchanged. Display missing product dossier explicitly, without interpreting absence as lack of potential. Source URLs remain external links, not evidence of causality.

## Consequences
Radar can display verified publication references for available MRI cases, including non-Pokémon categories. A matching card can display its investigation status. No inferred ROI, purchase authorization, AI API call, D1 write or deployment.

## Reversibility
Remove the `reactionCases` summary field and its Radar/product rendering; existing market snapshot integrity and storage remain unchanged.
