# ADR 033 — Full Outlook runner replay and identity integration regression

Date: 2026-11-20
Status: development-only; no live mailbox, remote D1 or deployed cron.

## Gap
Earlier tests verified Microsoft refresh, D1 lease and Graph Delta modules
individually. The exact composition of independently consented encrypted
credentials, refreshed Graph token, verified mailbox identity, parsed
Leboncoin notification, immutable D1 writer and encrypted Delta cursor
had no successful, multi-run integration test.

## Decision
Add `cloud/collector/test/leboncoin-runner-e2e.test.mjs` to the
Outlook CI suite and the overall Cloudflare collector test glob.

The test persists genuine WebCrypto AES-GCM ciphertext in a stateful D1
contract fixture, seeds an identity-bound refresh credential, and
executes `runOutlookLeboncoinCollection` with mocked Microsoft HTTP
responses. The first pass must rotate the credential, verify Graph
/me, parse a native HTML saved-search email, persist exactly one
immutable listing and save the Graph Delta checkpoint. A second
invocation reuses the rotated credential and saved cursor, imports
no duplicate listing and advances the cursor generation. The D1
owner lease must be released after each run.

A separate negative integration scenario supplies a mismatching
Microsoft Graph identity. It must fail before any Delta mailbox
request or listing write, and must release its run lease.

## Evidence and limitations
The test covers cross-module contracts and replay with a durable
test fixture, not a remote D1 server or actual Microsoft Graph.
Actual Wrangler local D1 migration checks are verified separately.
The test is entirely offline and contains no user data, mailbox
credential or external service call.

The separate Microsoft Entra app, operator Access policy and consent,
remote schema deployment, secret provisioning and authorized real
import remain blocked by external setup. This PR neither merges to
main nor deploys, schedules or purchases anything.
