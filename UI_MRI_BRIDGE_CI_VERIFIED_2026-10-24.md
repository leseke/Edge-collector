# EDGE UI MRI Bridge — CI verified 2026-10-24

## Exact GitHub Actions checkout
PR #3, branch `edge/ui-mri-bridge-001`, commit `5cc9e8b3c904470174787074a99933ee742f684c`.

GitHub Actions run ID **40112051994**, job **120925635622**: **SUCCESS**.

- Bridge unit tests: **17 / 17 PASS**.
- Complete offline suite: **351 tests run, OK (skipped=1)** (350 passed, one missing real recorded TCGdex response).
- Offline network attempts: **0**.
- Public file audit on actual Git checkout: **176 tracked files, 0 issues**.

Previous workflow attempts were red due to missing dependency `requests` and intentional `GITHUB_ACTIONS=true` SpendGuard rejection for simulated monthly reservations. The final workflow installs test-only `requests`, then runs the offline simulation under `env -u GITHUB_ACTIONS` in that test step only. The SpendGuard production code remains unchanged. This green workflow **does not independently prove** that the CI spend fail-closed behavior is correct; that must remain separately tested.

## Product scope
`intelligence/mri_public_adapter.py` converts *already editorially reviewed* research cases and evidence-gate results into a strict allowlisted `RESEARCH_ONLY` public JSON payload. This does not automatically analyze actors or publish live data; the curated input and gate qualification have to be supplied. No financial fields/BUY, no network source calls, no deployment or auto-push.

`preview/index.html` was statically inspected and tested via offline contract checks. **A full visual browser test remains outstanding.**

No main modification, no merge, no Pages deployment.
