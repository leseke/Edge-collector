# EDGE Outlook — Dedicated Cloudflare Worker deployment (V36)

Status: branch-only preparation, **not deployed**. Existing TCG Worker and
Vercel/Next.js application are out of scope. No production mailbox access.

## Why this package exists

The repository root `wrangler.jsonc` builds and deploys the Next.js app
(`edge-radar`). The existing `cloud/collector/src/index.ts` serves the
TCG collector and can schedule TCG/GCC work. Neither is appropriate as the
entrypoint for a mailbox-specific service.

This deployment instead uses:

- **Worker name**: `edge-outlook-collector`
- **Configuration**: `cloud/collector/wrangler.outlook.jsonc`
- **Dedicated entrypoint**: `cloud/collector/src/outlook-worker.ts`
- **Repo/branch**: `leseke/Edge-collector` /
  `edge/outlook-leboncoin-ingestion-001`
- **Deploy from repository root**:
  `npx wrangler deploy --config cloud/collector/wrangler.outlook.jsonc`

The `cloud/collector/wrangler.outlook.jsonc` main path is relative to the
config directory. It intentionally contains no D1 database ID, secrets,
cron triggers, custom domain or Microsoft account identifiers. Every
OUTLOOK route, consent, ingestion, sync, diagnostics and scheduling flag
defaults to the string `false`. The dedicated entrypoint contains
only the existing Outlook HTTP adapter: the TCG collection endpoint
and its scheduled tasks are not present.

## Cloudflare Git integration: important manual verification

The repository includes a `main` branch and other deployment configs.
Do **not** use the generic `npx wrangler deploy` command or assume the
Cloudflare Git UI deploys the desired branch automatically.

Before pressing Deploy, verify all three:
1. Selected production branch is exactly
   `edge/outlook-leboncoin-ingestion-001` (not `main`).
2. Project name is `edge-outlook-collector`; the build command can
   remain empty while the deploy command is the explicit command
   above, executed from repository root.
3. The integration actually allows branch/command settings. If the
   UI does not expose or confirm the branch selection, **STOP**.
   Do not gamble with an automatic deployment from `main`.
   Use an operator-controlled, branch-explicit Wrangler workflow
   after reviewing authentication, or an approved Git integration
   that clearly states which branch it will build.

For the initial code-only deployment, **do not** bind the
existing `edge-tcg-collector` D1 database and **do not** copy
`TRIGGER_SECRET` or any live Microsoft secret. The new Worker will
return HTTP 404 for all Outlook paths until a separately reviewed
activation. This is expected.

## OAuth URI only after confirmed Worker deployment

After Cloudflare reports and you independently verify the actual
`workers.dev` hostname of this new Worker, set the exact **Web**
redirect URI in the Microsoft Entra application:

`https://<VERIFIED-EDGE-OUTLOOK-WORKER-HOST>/auth/microsoft/callback`

Never point the Microsoft redirect at the separate
`edge-tcg-collector.ylan-seke.workers.dev`, or at Vercel,
unless the callback handler is genuinely deployed there.
Do not enable implicit grant/hybrid tokens.

The Microsoft Entra application has been registered manually by the
operator and configured with delegated `Mail.Read`, `User.Read` and
`offline_access`. Registration and configured scopes are **not**
the same as consent or a functional Worker callback.

## Later, separately authorized activation gates

Before enabling ANY route or entering Microsoft credentials:

1. Configure a private Cloudflare Access application/policy bound to
   the Worker host, verify JWT issuer + app audience and pin exactly
   one operator subject. Verify callback behavior through Access.
2. Provision a **separate**, access-limited D1 database, apply
   and verify the complete Outlook schema/migrations in the correct
   order and bind it to `DB` on this Worker only. No guessed IDs.
3. Store `OUTLOOK_CLIENT_ID`, `OUTLOOK_CLIENT_SECRET`,
   `OUTLOOK_REDIRECT_URI`, `OUTLOOK_TENANT` (personal Outlook
   uses the `consumers` authorization endpoint where appropriate),
   encryption keys and Access values through Cloudflare's secure
   configuration. Never commit secrets, tokens or PKCE verifiers.
4. Independently test redirect URI equality, private Access session,
   D1 migrations, authorization code+PKCE flow, delegated consent
   and mailbox subject binding. With Microsoft personal accounts,
   do not confuse the Entra registration tenant with the Microsoft
   OAuth `consumers` authority used by the collector.
5. Apply a measured first import with proven sender allowlist and
   de-duplication, then separately decide when to turn on scheduled
   collection.

No code in this package automates any step above. It makes the
first Worker deploy isolated and fail-closed.

## Offline verification

```sh
node --experimental-strip-types --test cloud/collector/test/outlook-worker-isolation.test.mjs
npx tsc --project cloud/collector/tsconfig.json
npx wrangler deploy --dry-run --config cloud/collector/wrangler.outlook.jsonc
```

The CI tests run without accessing Cloudflare, Microsoft, or a real D1.
A successful build or dry run is **not proof of deployment**.
