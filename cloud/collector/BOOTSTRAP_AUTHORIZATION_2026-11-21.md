# EDGE Outlook isolated bootstrap authorization — 2026-11-21

Operator authorization for the first deployment of only `edge-outlook-collector` from branch `edge/outlook-leboncoin-ingestion-001`.

Scope: initial default-disabled Worker script only. Do not modify `main`, `edge-tcg-collector`, D1 schemas, Microsoft mailbox permissions, cron schedules, or existing deployments.

Deployment workflow must reject unexpected branch, actor, missing environment credentials, existing Worker script, config mismatches, or failed offline tests. If any gate fails, stop without retrying automatically.

This note contains no secrets or account identifiers.

## Controlled retry after dependency repair

The prior bootstrap stopped at `npm ci` because the root lockfile was missing. The branch now includes a checked-in package-lock.json and aligned package.json. Re-run the same guarded bootstrap; if any guard, test or build fails, stop without repeated deployment attempts.
