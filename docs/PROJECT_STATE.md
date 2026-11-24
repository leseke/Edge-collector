# EDGE — canonical handoff

Updated 2026-11-24. Development branch: edge/tcg-multi-agent-orchestration-001. PR #5 (draft; recheck live status). Main must remain untouched.

## Verified baseline
- Next.js dashboard reads latest.json from edge/commercial-history and validates report and raw payload hashes. Current UI is Pokémon-card observations, not a comprehensive TCG catalog.
- Card evidence dossier, JSON corpus export and same-tab local inquiry handoff exist. Local companion is experimental and requires explicit local setup.
- TypeScript corpus generator and Python validator contract test exist; CI for e374e033dd391323c43923038d5f170769c20647 succeeded (Next.js #224, offline #301). Whether Node-dependent test was skipped needs job-log confirmation.
- app/lib/tcg-history.ts and tests/tcg_history_contract.mjs exist. Historical index is not yet confirmed wired into the dashboard. Standard history index paths tested returned 404; actual publisher layout needs inspection.
- Latest inspected commercial capture: 45179610868-1, 2026-11-23, PARTIAL. Do not treat as current without refreshing.
- No full audit or production readiness claim. Active offers, completed sales coverage, autonomous discovery, portfolio and full UI integration need verification.

## Next executable delivery
Market Explorer vertical slice: inspect existing routes and collectors, then implement a connected searchable/filterable product catalog and detailed product view with actual available data. Reuse existing code and expose missing offers/sales honestly. Inspect historical publisher to connect real historical data rather than invent an index. Group changes, test and update this file.

## Handoff discipline
Each session records actual delivered outcomes, code commit IDs, validation evidence, pending tests, known blockers and next executable task here. Reconcile against current HEAD, including automation commits. No conversation memory is required.
