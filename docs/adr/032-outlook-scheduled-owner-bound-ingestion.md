# ADR 032 — Explicitly gated scheduled Outlook collection

Date: 2026-11-20
Status: development branch only; no cron provisioned, no deployment.

## Context
The Outlook importer had an authenticated operator-triggered diagnostic
endpoint, but it was not invoked from the isolated Cloudflare Worker's
existing scheduled handler. The user wants automatic recurring ingestion
without entering mailbox IDs or ad information manually.

## Decision
Add `leboncoin-scheduled.mjs` and invoke it from the already existing
`scheduled` event in the isolated collector Worker.

- **Default inert:** both `OUTLOOK_SCHEDULE_ENABLED=true` and
  `OUTLOOK_INGEST_ENABLED=true` are required; absent flags do no D1,
  Microsoft or Access network work.
- **Owner derivation:** an event has no operator JWT. The server must have
  exactly one operator subject explicitly listed in
  `CF_ACCESS_ALLOWED_SUBJECTS`, plus the exact Access team URL and AUD.
  `deriveCloudflareAccessOwnerKey` uses the same validated SHA-256
  derivation as signed Access JWT verification. No caller-supplied owner
  or mailbox ID may be accepted by the scheduled event.
- **Per-run bound:** each cron invocation checks up to 3 Microsoft Graph
  Delta pages, saving immutable observations and encrypted cursors with
  the existing per-owner D1 run lease and fencing rules.
- **Outputs:** the schedule returns only status/active/complete flags,
  never mailbox metadata, tokens, message content or listing contents.
- **Failure isolation:** an Outlook exception is caught and logged as a
  fixed non-secret error code. The pre-existing TCG and GCC scheduled
  collection paths continue running independently.

## Operational prerequisites
No cron trigger was created. The code is only a new handler within an
existing isolated Worker source. It must not be enabled until:
1. The isolated Worker is intentionally deployed with the approved
   scheduled trigger (existing cron must be reviewed, including frequency).
2. Microsoft Entra confidential-client app registration, HTTPS redirect
   and independent delegated OAuth consent exist.
3. Cloudflare Access issuer, audience and the single operator subject
   match the consent identity that owns the encrypted refresh credential.
4. Remote D1 migrations are applied after explicit approval and verified.
5. Encryption keys and secrets are provisioned privately.
6. A human-authorized manual import verifies real Graph /me identity,
   snapshot provenance and D1 checkpoint recovery.
7. Runtime quotas, retry/alerting, revocation and duplicate handling
   are validated before setting `OUTLOOK_SCHEDULE_ENABLED=true`.

This implementation does not create a deployed endpoint, activate a
cron or authorize purchases. `main` remains unchanged.

## Tests
Offline tests assert zero work with disabled gates, deterministic
matching owner derivation, rejection of invalid/multiple subjects,
bounded maxPages, handling of BUSY and redaction. Full existing
Cloudflare CI verifies the isolated Worker build.
