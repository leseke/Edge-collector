# AI-002D — Official-page snapshot monitoring (opt-in)

This is a **narrow, non-financial signal**: detects changes to an official Pokémon China TCG page across capture dates. Changes to the page are *not* claims about market demand, prices, popularity, supply, or sold volume.

- Existing EDGE modules, policy, allocation, and private budget are unchanged.
- The default execution denies network access. Explicit `--allow-live-fetch` is required.
- HTTPS host and path are allowlisted; redirects refused; request timeout 12s; bounded HTML, no retries, no paid endpoints.
- Does not import the contents of the page as verified claims or assume reuse rights. It logs only timestamps and a content digest.
- `snapshots.jsonl` is append-only. A new observation on a different day creates a new event; there is no invented intermediate point.
- Histories consist of **content hashes**, not price series. The site may update design elements, so changes are not necessarily meaningful market news.

## Offline test

`python -m unittest tests.test_ai002d -v`

## Explicit opt-in live capture (not run as part of tests)

`python -m intelligence.market_monitor --store private_market_monitor --allow-live-fetch`

Re-run on a later date to compare. Do not schedule until terms, robots policy and operational budget have been approved. Store should remain private until redistribution rights are reviewed.
