# EDGE Outlook — controlled remote D1 migration (not yet executed)

Target only: `edge-outlook-history`, UUID `e0ca923f-8af2-4182-9df8-c8ef05ce5000`, Cloudflare account `701b40ddbcb6c7b6f6ff9180e27f6648`.

The Worker `edge-outlook-collector` is deployed independently. The migration workflow does **not** deploy or bind that Worker, change `main`, touch the TCG database, activate a scheduler, or access an Outlook mailbox.

## GitHub environment setup (operator action)

Create a new repository environment `edge-outlook-d1-migration`, restrict deployment branches to **exactly** `edge/outlook-leboncoin-ingestion-001`, and configure any suitable reviewer approvals. Do not use the existing Workers Scripts token for D1.

Add environment-scoped:
- Secret `OUTLOOK_D1_MIGRATION_CLOUDFLARE_API_TOKEN` — a newly created, short-lived, account-scoped Cloudflare token with D1 edit permission for the verified account only. Do not paste the token into chat or source control.
- Nonsecret environment variable `OUTLOOK_D1_MIGRATION_CLOUDFLARE_ACCOUNT_ID` — exact account ID `701b40ddbcb6c7b6f6ff9180e27f6648`.

Cloudflare's D1 permission is account scoped; it may allow writes to other databases. The independent name+UUID checks and environment/branch/commit restrictions therefore matter; never treat the token itself as database-specific least privilege.

## Launch — separate operator authorization

The branch-only workflow `.github/workflows/outlook-d1-isolated-migrate.yml` executes only on an owner commit whose **entire commit message** equals:

`chore(outlook): authorize isolated d1 migration`

Do not create that commit until the operator has verified the environment secret, branch rule, and database is empty. Ordinary preparation commits do not run the migration.

The workflow:
1. Runs `npm ci` from the tracked lockfile and statically checks the staged Outlook-only config and additive SQL.
2. Checks the Cloudflare account ID, exact D1 UUID and name, optional jurisdiction metadata, and reads `sqlite_master` without inspecting user data.
3. **Refuses** to write if any non-system table already exists. Partial migration requires manual investigation rather than blind re-run.
4. Applies only `003` through `006` to the exact D1 database using explicit `--remote` and the staged Wrangler config.
5. Verifies six `lbc_*` tables and four immutability triggers on the remote database.

A preflight does not rule out a concurrent external database change between checks and SQL execution. Use a maintenance window; do not run two migrations concurrently. Production D1 changes are not transactionally rolled back as a group if a later migration fails.

## After success

Verify the six tables again in the Cloudflare D1 console and keep automatic Outlook ingestion disabled. **Only in a separate, reviewed step** deploy the D1 binding with `cloud/collector/wrangler.outlook.d1.staged.jsonc`. Do not use the original bootstrap workflow; it is intentionally first-deploy-only and rejects an existing Worker.

Do not configure Microsoft secrets or activate OAuth/Graph until Cloudflare Access JWT issuer/audience and trusted owner identity have been independently validated.

## Operator-authorized execution — 2026-11-22

The operator confirmed the dedicated `edge-outlook-d1-migration` GitHub environment, branch restriction, secret and account variable. This commit authorizes one guarded migration attempt on the isolated D1 target. Stop on any failed step; do not rerun failed/partially applied migrations automatically. No Worker deployment or Microsoft mailbox activation authorized.

## Controlled retry after corrected SQL preflight — 2026-11-22

Operator requested a single retry following the false-positive rejection of an immutable `BEFORE UPDATE ON` trigger. The previous run failed at static SQL verification, before any remote Cloudflare request. The migration remains conditioned on exact Cloudflare account, database UUID, empty schema and subsequent verification. Do not automatically rerun if any step fails; investigate before further authorization.
