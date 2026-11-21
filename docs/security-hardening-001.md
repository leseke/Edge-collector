# EDGE — Security hardening 001

Status: development only. Base: edge/outlook-leboncoin-ingestion-001 at 58e7bc1afa329f48248bf67afefd050ab57741b5. Branch: edge/security-hardening-001.

## Threats
- The Cloudflare build workflow previously contained a push-triggered remote D1 provision/migration/Worker deploy/cron/secret/collection path.
- A second path deployed a preview based on a magic commit message.
- A separate D1 provisioning workflow created remote resources when the workflow file was pushed.
- The repository default branch is not protected; administrative branch rules require a separate, explicitly approved configuration.
- Node and Python dependency lockfiles, secret-history scan and advisory checks are pending.

## Change
- Retain Cloudflare compilation and local D1/agent tests. Remove remote mutation paths from cloudflare-build.yml.
- Make edge-d1-provision.yml manual and non-mutating, with no cloud credentials.
- Add an offline workflow policy test and a read-only CI job.

## Limits
These changes affect this development branch only. Existing workflows and deployed Workers on other branches remain untouched. Cloudflare/D1 already deployed outside GitHub are neither inspected nor changed. No production access, deployment, merge, purchase or API spending is authorized here.

## Promotion gate
1. Verify all workflow changes and CI test outcomes, including this policy test, Cloudflare build and Outlook regression tests.
2. Establish main branch rules with PR, required checks, no force-push, no bypass, and appropriate review. GitHub rules administration is a separate explicit change.
3. Create a distinct `workflow_dispatch` infrastructure deployment workflow, referencing a protected environment with required reviewers and least-privilege credentials, before restoring any remote mutation.
4. Generate a committed npm lockfile, move to npm ci, pin GitHub Actions by verified full commit SHAs, and lock/audit Python dependencies.
5. Run a full-history secret scan and dependency vulnerability scan in a controlled environment. Review false positives privately; rotate any confirmed leaked secrets without logging them.
6. Require evidence from staging and a rollback plan before any production deployment.

## Rollback
Revert the security commits on the isolated branch. Do not revert protections or re-enable deployment on main without separate review.

## Dependency remediation — 2026-11-21
- GitHub Actions generated package-lock.json with npm v11 / Node 24; install steps use npm ci on primary Next.js and Cloudflare builds.
- Wrangler changed 4.148.0 -> 4.165.0; @cloudflare/workers-types changed 5.20261115.1 -> 5.20261118.1 to satisfy Wrangler peer requirements.
- Generated lockfile resolves Wrangler/types consistently; npm audit fix --package-lock-only without --force eliminated the four high advisories observed in the original lockfile, but still reports 3 moderate advisories in OpenNext/glob/minimatch pending further triage. Do not force a potentially breaking dependency upgrade.
- CI on the resulting lockfile and latest branch commit must be evaluated separately. Python requirements are still unpinned and require a subsequent reproducibility change.
- Earlier targeted GitHub Actions Gitleaks and pip-audit jobs completed successfully; this is not proof of absence of all historical secrets or supply-chain vulnerabilities.

## Credential isolation and deployment review — 2026-11-21

- Removed `dsh-real-d1-readonly` and `verify-cloudflare-access` jobs from the general Cloudflare build workflow: neither PR code nor an ordinary development-branch push can acquire a Cloudflare token through this workflow.
- The general Cloudflare build now has no `secrets.*` references; CI policy tests enforce this constraint.
- Added `.github/workflows/deployment-review.yml`, a manual review-dossier workflow with read-only repository permissions, SHA matching, metadata validation, and zero Cloudflare secrets or deployment commands. It **cannot deploy**. Manual workflows must first be available on the default GitHub branch before GitHub exposes the Run workflow control.
- Existing deployed infrastructure, account-side Cloudflare Access policy, and other branches remain unchanged. A separate protected-environment deployment procedure must be reviewed and authorized explicitly; this preparation does not grant deployment access.
- The repository administration step is still pending: `main` remained unprotected at the last metadata check. See `docs/github-protection-proposal.md`.

## GitHub Pages publication gate — 2026-11-21

- The repository Pages workflow previously deployed automatically on selected pushes to `main`. In this isolated security PR only, changed to a **manual `workflow_dispatch`** that requires an exact reviewed main-branch SHA and a safe change reference.
- Checkout uses `persist-credentials: false`; the site remains built and validated before any publication job runs. All four Pages-related GitHub Actions are pinned to verified, immutable commit SHAs.
- The deploy job still references GitHub's `github-pages` environment. An administrator must confirm it has independent required reviewers, restrictions and no bypass before any deployment. The manual trigger and SHA check do not independently guarantee a second person's approval.
- **Current `main` still contains its existing Pages workflow**: no change takes effect on the default branch until separately approved integration. No deployment has been performed as part of this change. The scheduled independent market collection workflows are unaffected.
