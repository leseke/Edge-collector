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
