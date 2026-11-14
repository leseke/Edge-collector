# Discovery V1 — isolated foundation

Experimental proposal. This directory does not alter `radar.json`, `edge_engine.py`, `index.html`, or existing collectors.

## Scope
- Accept JSON observations supplied by future authorized source adapters.
- Validate HTTPS provenance, observation timestamp with timezone, and positive price.
- Deduplicate by source/external ID.
- Emit auditable candidates and rejections. **Asking price is not a completed sale.**
- Enforce `CASH` and zero allocations on all candidate-only outputs.

## Not yet implemented
Live product search, source adapters, scheduled GitHub Actions, user-triggered search endpoint, evidence verification of completed sales, financial valuation, AI investigation, or buy signals. Do not market this foundation as autonomous research.

## Test
`python -m unittest discover -s tests -p 'test_discovery_engine.py'`

## Demo
`python -m discovery.engine --input discovery/sample_observations.json --output /tmp/edge-candidates.json --campaign pilot-collectibles`

All sample listings are fictitious. No operational production data is produced by the demo.

## Governance
Merge only after reviewing integration with the Option A candidate and the repository's decision/portfolio policy. No modifications to production workflow or main branch in this proposal.
