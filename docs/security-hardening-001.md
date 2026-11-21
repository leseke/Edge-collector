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
