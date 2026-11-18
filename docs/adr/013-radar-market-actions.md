# 013. Radar market actions

## Context

The Radar opened with collection counters and methodology. The isolated preview did not have the sales database binding, so new paid auction results were absent. An unrelated publication dossier could appear among Pokémon results.

## Options

1. Keep the report layout and add a glossary.
2. Put paid prices and the listing comparison first, with supporting evidence available on demand.

## Decision

Use option 2 on the existing /mri route. Give the isolated preview the existing D1 database through the SALES_DB binding. The Radar issues SELECT queries only, reads the existing paid_market_sales fields, and limits the visible list to eight documented transactions with source links. Comparison uses the exact variant key, including language, edition, and grade or sealed status. Keep the reviewed history as a fallback. Group Cardmarket aggregates and publication sources behind disclosure controls.

## Consequences

The page can answer what sold and give a comparison for a supported listing. Recent sales and trends remain subject to collection coverage. A listing with too few matches shows a monitoring status. The preview smoke test requires an actual linked sale in the response. There is no new route, D1 migration, provider call, or collector write.

## Reversibility

Revert the view and remove the preview-only binding configuration. No stored observations need to be changed.
