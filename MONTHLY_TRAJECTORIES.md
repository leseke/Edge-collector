# EDGE — Monthly trajectory research v1

The `trajectory_history.py` workflow stage reads only the checked normalized historical import (SHA-256 checked against that run's import metadata). Native scope remains Poland/PLN/monthly maximum, June 2018–June 2023. Outputs: `trajectory_summary.json`, `trajectory_report.md`, full source-linked audit `trajectory_research.json.gz`. Audit JSON compression is deterministic and omits generation time so an unchanged experiment does not create new large Git blobs every run. The snapshot summary records generation time and audit checksum.

## Fixed experiment, not optimized after seeing its scores

Features: four consecutive nonmissing monthly prices, represented by three successive logarithmic price changes. No later-known popularity, release/retirement status, future availability or realised outcome appears in the query features. Outcomes are endpoint changes at 1/3/6/12 months, requiring every intervening month to be present and positive. Zeros were converted to missing by the importer; they are not zero-price bargains or negative outcomes.

Reference retrieval: same dataset/scope, calendar month within circular distance one, price min/max ratio at least 0.5, mean absolute difference between the three log changes at most 0.10. Every precedent target month must be strictly earlier than the query month. Self and other episodes sharing the query's conservatively extracted numeric URL reference hint are excluded. One episode per reference hint is retained, sorted by distance then episode ID. At most twenty neighbours; at least ten required before numeric estimates. These are research heuristics, not validated confidence/safety thresholds. The URL reference hint is not official variant identity; remaining dependence and identity limitations are explicit.

Conditional estimates: proportion of retained outcomes above zero, median change, empirical interpolated p10/p90. These are labelled computed estimates. The dispersion is a historical range, not a calibrated forecast interval or a confidence interval. Price phases use only the cumulative three-month change (rising above +1%, falling below −1%, otherwise stable within 1%); phases do not assert attention, scarcity, FOMO or motivations.

Evaluation queries: twenty distinct reference hints selected per quarter by fixed SHA-256 order, quarter ends March 2021–June 2023 (up to 200 queries). Sampling occurs before future outcome completeness is examined. Query outcomes are joined after estimation. Results missing due to the dataset end or incomplete series remain separately counted. Metrics are paired on the same queries with enough analogues and a measured future target.

Comparisons: MAE of the analogue median versus both zero price change and the median of past outcomes; Brier score versus the frequency of positive past outcomes. The simple past cohort uses the latest eligible episode per other reference hint, subject to the same strict temporal cutoff but without the analogue shape/season/price filters. Direction confusion counts use a fixed 0.5 positive-frequency cutoff. Lower MAE/Brier is better. No profitability calculation is performed.

## Interpretation

This is ordered retrospective research, not a validated point-in-time simulation or independent predictive test. The public file was assembled later; original monthly publication lag/revisions and the complete market universe are not known. Price aggregates do not establish completed transactions, executability, volumes or liquidity. Windows/series/markets overlap, and surviving complete observations can be unrepresentative. No significance claim, future calibration, reliable optimal entry/exit, causal effect, net return or buy/sell instruction is emitted.

Rules are versioned in code; changes after viewing results require a new method version and an untouched future evaluation set before predictive claims. Baselines and unfavourable horizons must remain visible. The final workflow check surfaces research-stage failures after evidence archiving.
