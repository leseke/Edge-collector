# ADR 022 — Explicit Outlook collection runner and CI flake remediation

Status: development only, no runtime deployment or schedule.

## Context
The standalone Microsoft consent, D1 persistence and Graph Delta modules
were not yet composed into a single invocation. The shared Cloudflare build
job failed once because a JWT signature-negative test mutated only the final
Base64URL character, which can change padding bits without changing decoded
signature bytes. A separate Outlook-only workflow passed; that was not proof
of the shared pipeline passing.

## Options
1. Enable scheduled polling immediately: unsafe without independently
   consented Microsoft credentials and provisioned Cloudflare/D1 services.
2. Compose the components in a feature-disabled runner, enforce identity
   verification on every renewal, and test refusal without consent.
3. Continue adding isolated OAuth primitives without an invocation contract.

## Decision
Choose option 2:
- `leboncoin-runner.mjs` orchestrates encrypted credential read, Microsoft
  delegated token renewal, Graph account identity check, bounded Delta
  paging, append-only D1 observations and encrypted checkpoint.
- `OUTLOOK_INGEST_ENABLED=true` is necessary but insufficient: a verified
  account ID and separately authorized refresh token must exist. The runner
  is **not wired to a cron, HTTP route or existing production Worker**.
- Mailbox owner key must come from a trusted authenticated principal, not
  a client string.
- Check `OUTLOOK_DELTA_ENCRYPTION_KEY` in the readiness report.
- Mutate the first significant signature character in JWT rejection tests,
  not the last character, to deterministically corrupt the signed bytes.

## Activation barriers
Independent Microsoft Entra registration and user consent, Cloudflare Access
policy/operator configuration, D1 migration/provision, secret injection,
verified scheduled-run identity, concurrency lock, timeout/retry/monitoring
and explicit production deployment authorization are still required.

## Verification
Run Outlook tests and the entire Cloudflare collector suite. Distinguish
verified CI execution from expected results; no production data is inferred
from synthetic fixtures.

## Reversibility
Additive modules and tests on the feature branch; no main or production
configuration changed.
