# EDGE — Proposed GitHub protection controls (NOT APPLIED)

This document is a review proposal only. The GitHub connector used for this audit cannot modify branch protection or repository rulesets. The actual `main` branch is not protected according to the latest available GitHub branch metadata.

## Main branch ruleset

Target: `refs/heads/main`. Enforce for all push-capable actors, including repository administrators except a documented break-glass identity.

- Require a pull request before merge, at least one independent approving review, and dismissal of stale approvals.
- Require resolved review conversations.
- Require passing status checks. Select checks that actually run on every PR to `main`, with exact job names confirmed from a successful trial PR. The initial candidates are:
  - `Cloudflare Workers build / cloudflare` (check actual GitHub check-run label)
  - `Next.js build / nextjs`
  - `EDGE security workflow policy / workflow-policy`
  - `EDGE security dependency and history audit / npm dependency advisories`
  - `EDGE security dependency and history audit / Python requirements advisory scan`
  - `EDGE security dependency and history audit / Check Git history for leaked credentials`
  - `EDGE MRI offline tests / offline-tests`
  Not every workflow is necessarily deployed to `main`; **do not mark a check required until its workflow is present on the target branch and actually runs for the relevant PR event**. Job label may differ across API/UI.
- Require branches to be up to date before merge if necessary, without imposing impossible checks.
- Prohibit force pushes, deletion, and unsigned or bypassed changes where feasible.
- Restrict bypass permissions to a narrowly identified emergency process. Audit all bypass events.
- Protect GitHub Actions workflow edits via CODEOWNERS review if the repository has additional independent reviewers.

## Additional controls
- Set default `GITHUB_TOKEN` workflow permissions to read-only; request `contents: write` only per publishing job.
- Store Cloudflare credentials in an environment with required reviewers, not on general PR/build jobs.
- Configure an approval-gated infrastructure workflow separately from build/test CI, with Cloudflare tokens scoped to exact required resources.
- Restrict forks and untrusted pull requests from accessing credentials; avoid `pull_request_target` with unreviewed code.
- Require license/advisory and history-secret checks before branch promotion.

## Deployment plan
1. Verify a test PR can run every proposed required check.
2. Configure GitHub repository Settings > Rules > Rulesets or Settings > Branches using repository administration credentials, separately from this code PR.
3. Check effective `main` branch protection through GitHub API after applying rules.
4. Verify that an unreviewed test PR, direct push, force push, and failing CI are blocked as expected.
5. Record the ruleset identifier and audit events in a private operational register (no secrets).

## Important limitations
These instructions do not protect a branch until applied on GitHub. This file does not grant new rights or touch `main`. No GitHub repository setting has been changed by this audit.

## Additional deployment review blocker: Outlook bootstrap, 2026-11-21

The PR target `edge/outlook-leboncoin-ingestion-001` received three commits after this security branch was created, adding `.github/workflows/outlook-bootstrap-deploy.yml` and changing `cloud/collector/OUTLOOK_WORKER_DEPLOY.md`. This is a separate, later workflow not yet included in the isolated security branch.

The new bootstrap workflow contains a push-based deployment condition requiring `github.actor == 'leseke'` and an exact head commit message `chore(outlook): authorize isolated bootstrap deployment`. It also declares an `edge-outlook-bootstrap` environment and uses environment-scoped Cloudflare credentials. However, this repository connection cannot verify whether that environment actually requires reviewer approval, and a commit-message gate is not itself explicit deployment approval.

**Do not promote the security PR as a complete closure of deployment P0 until this new workflow is reviewed.**

Proposed change before integration:
1. Remove push-based deployment activation and the commit-message authorizer, leaving `workflow_dispatch` only for a remote deployment workflow.
2. Require an explicitly reviewed full commit SHA and positive approval record; verify the SHA corresponds to the tested change.
3. Configure `edge-outlook-bootstrap` as a protected environment with independent required reviewers, deployment-branch restrictions and narrow Cloudflare credentials.
4. Keep read-only/offline bootstrap validation as a separate secretless workflow that runs on PRs.
5. Verify manual workflow visibility and conditions in a controlled branch rollout before enabling remote mutation.
6. Reconcile the three newer Outlook commits into the security branch without overwriting unrelated changes; rerun full CI and review merge conflicts.

A conditional regression test in `tests/security-workflow-policy.test.mjs` enforces absence of this magic-commit deployment mechanism once the Outlook bootstrap workflow is present in the same tree.

The new Outlook workflow is on the **PR target branch**, not yet modified by this security branch. No new Cloudflare deployment has been performed here.
