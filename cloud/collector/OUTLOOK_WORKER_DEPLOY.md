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

## Branch-only GitHub Actions deployment — prepared, not triggered (V37)

The alternative controlled workflow is
[`.github/workflows/outlook-bootstrap-deploy.yml`](../../.github/workflows/outlook-bootstrap-deploy.yml).

The Cloudflare Git UI did not show an assured production branch. **Exit that
wizard without pressing Deploy**; its use is not required for this route.

This workflow runs a deployment job ONLY on an authorized `push` to
`edge/outlook-leboncoin-ingestion-001` by GitHub actor `leseke` and ONLY
when the last commit message is exactly:

```text
chore(outlook): authorize isolated bootstrap deployment
```

All other commits skip the job, including this workflow's creation. This is
a deliberate commit-based approval mechanism, not a scheduled deployment.

### One-time setup by the GitHub/Cloudflare account owner

1. On the repository, open **Settings → Environments** and create
   `edge-outlook-bootstrap`. Restrict deployment branches to the exact
   `edge/outlook-leboncoin-ingestion-001` branch. Configure required reviewers
   when available and suitable; a reviewer different from the initiator may
   be required if self-review is disabled. Do not assume this protection
   exists until you verify it in GitHub.
2. In this environment **only**, configure secret
   `OUTLOOK_BOOTSTRAP_CLOUDFLARE_API_TOKEN`: a dedicated, minimally scoped
   Cloudflare API token that is allowed to create/edit Workers scripts in
   the intended account. Do NOT reuse a general personal API key or paste
   a token in chat, source, issue, PR, or workflow variable.
3. Configure environment variable
   `OUTLOOK_BOOTSTRAP_CLOUDFLARE_ACCOUNT_ID` to the verified account
   identifier (32 lowercase hex digits). This is not the tenant ID from
   Microsoft. We never guess its value.
4. Review the current branch commit and the dedicated config before any
   deployment. Make an explicit operator-authored commit on this branch
   with the EXACT message above when you decide to bootstrap. One safe
   option is editing an innocuous documentation line via GitHub's web
   editor and setting the commit message manually. **Do not create this
   approval commit until the environment and token are verified.**

The workflow then performs an exact-SHA checkout, `npm ci`, validates the
Outlook-only config, runs offline isolation tests, and executes a real
Wrangler dry-run. It requires the environment-scoped token and checks whether
the new Worker script already exists. It **fails closed** on a missing
token/account ID, API error, invalid config, different source branch or actor,
or an existing `edge-outlook-collector` script. Only a first-time isolated
Worker deployment is permitted. It never changes existing TCG Worker,
D1 schemas, or Microsoft app settings.

Even after this bootstrap, OAuth routes are disabled. The Cloudflare
`workers.dev` URL must be read from the actual deployment and Cloudflare
Access must be configured and validated before Microsoft authorization.

**GitHub limitation:** a newly added `workflow_dispatch` button normally
requires the workflow file on the repository's default branch (`main`).
We deliberately do NOT modify `main`; use the controlled commit trigger
instead, or obtain a separately reviewed deployment path later. This
workflow cannot be activated solely by manually selecting a branch in the
GitHub Actions UI at the current stage.
