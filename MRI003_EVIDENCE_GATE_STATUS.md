# MRI-003 — Historical evidence gate

**Branch:** `edge/mri-003-historical-evidence-gate` derived from MRI-002. No changes to `main`.

## What was verified independently (2026-10-22)
- Pokémon China official announcement dated **2022-09-21**: https://www.pokemon.cn/tcg/product/16380.html
- Pokémon China later release detail dated **2022-09-28**: https://www.pokemon.cn/tcg/other/17201.html
- Pokémon China later organized-play announcement dated **2022-10-27**: https://www.pokemon.cn/tcg/event/16369.html
- LEGO official 10365 announcement dated **2025-08-26**: https://www.lego.com/en-us/aboutus/news/2025/august/lego-icons-captain-jack-sparrow-s-pirate-ship
- Brick Fanatics publication dated **2025-08-26**, citing older edition *asking* prices, not concluded sales: https://www.brickfanatics.com/lego-10365-jack-sparrow-pirate-ship-revealed

## Distinction enforced
Publication date is **not** a proven date of capture by EDGE. All original documents were located/retrieved in 2026. Both pilot candidates are therefore `replay_ready=false` unless independently verifiable contemporary captures are identified. A publisher-supplied date alone cannot be used as `observed_at` in MRI-001 or MRI-002 for a purported real historical replay.

`intelligence/historical_evidence_gate.py` validates provenance metadata and requires an archive/capture log timestamp on/before cutoff. **It does not independently cryptographically authenticate external archive URLs**; this requires an additional retrieval/verification layer.

`investigation/fixtures/mri_003_historical_evidence_cases.json` records exact source URLs with explicit `publisher_date_only` statuses. Do not claim that EDGE made predictions in 2022 or 2025. No concluded-sales data, ROI or calibrated forecast score has been established.

## Tests
`python -m unittest tests.test_historical_evidence_gate -v`

Nine test cases have been added; **no passing test result is claimed for these nine tests in this delivery** until an execution verifies them. The previous MRI-002 325-test reconstructed offline suite is a separate, earlier result and does not validate the new module. CI/full-suite and fresh disclosure checks remain open.

## Next steps
Gather independent contemporaneous snapshots and independently timestamped market outcome measurements; reject stale/retrospective sources, then freeze hypotheses and compare against neutral and negative cases. Maintain CASH and the existing financial gate regardless of analytical excitement.
