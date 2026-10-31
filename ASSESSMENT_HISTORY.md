# Observed dossiers and separate model estimates

Current user policy (31 October 2026): source-linked observations are required.
Generated probabilities are allowed when explicitly labelled as estimates, with
method, sample size and uncertainty. They are never recorded as observed prices
or transactions. Previous hypothetical snapshots remain historical archives.

Current observation dossiers contain publication metadata, latest real asking
prices with capture timestamps, stock declarations, source checks and missing
data. Narrative theses, inferred actor motives, research-priority scores and
hypothetical price scenarios are no longer exported by the assessment stage.
No missing price, cost or transaction is filled with an assumption.

`probabilities.json` is a separate computed-estimate artifact. The current model
counts product/publication-UTC-day/horizon episodes with measured reaction
windows. Snapshot replays do not add trials. Median asking-price changes across
available measurements define outcomes; these are not profit or sale outcomes.
At least five episodes are required before displaying an empirical frequency.
A Wilson binomial reference interval is provided, with the independence and
future-calibration limitations explicitly retained. No percentage is generated
for insufficient data. This is a historical-frequency estimate, not a validated
future forecast. Raw observations and estimates are separately labelled.

Every run preserves dated outputs and a manifest. Revised dossier fingerprints
now track observations and data gaps, not hypothetical narratives. The schema
transition itself is recorded in the next snapshot; old archives are untouched.
