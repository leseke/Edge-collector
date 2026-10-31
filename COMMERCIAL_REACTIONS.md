# Observed retail transitions and follow-up

Publication reactions and retail transitions are separate cohorts. Existing
retail events are now followed using the actual observations in the history.
Both before/after records must match product, seller, URL, currency, timestamp,
field value and evidence hash. Unverified pointers and indicative TCGdex changes
are excluded from the retail cohort; no historical observation is invented.

The transition's exact occurrence time is unknown between two captures. Follow-up
anchors at the observation-window end, explicitly labelled as detection time.
Subsequent displayed prices and declared stock are measured on the same source.
A source-specific stockout does not establish a market-wide shortage or sale.

Windows at 24, 72 and 168 hours require a successful capture in the following six
hours. Pending horizons, awaited captures and missed windows remain distinct.
Failed or unknown stock captures do not become negative outcomes. No late record
is backfilled into an earlier window. Immediate/latest observed changes remain
separate from these horizon measurements.

A separate empirical estimator targets declared IN_STOCK status at that reference
capture after a detected stockout. It does not estimate a restock at any point in
the interval, profit, liquidity or causal impact. Episode IDs are deduplicated.
Five measured episodes are required for a numeric historical frequency. Wilson
binomial reference intervals are provided; independence and future calibration
remain unverified. Publication probability estimates are not mixed with these
source-stock episodes. Actual inputs and computed estimates are separately typed.

Each scheduled run appends commercial_reactions.json, a readable report and
market_event_probabilities.json before the final manifest. Historical files stay
unchanged. This stage adds no external requests, purchases or paid integrations.
