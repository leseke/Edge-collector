# ADR 021 — Outlook activation readiness is not proof of access

Date: 2026-11-19
Status: development-only. No production enablement.

## Context
The Outlook connector has gained authenticated consent and incremental read
building blocks, but no independently registered Microsoft application,
Cloudflare Access operator policy or deployed D1 migrations. Treating the
presence of environment variables as a successful connection would falsely
label the collector as active.

## Options considered
1. Infer readiness when secrets exist: easy but conflates configuration,
   user consent, successful Graph requests, D1 schema and scheduler state.
2. Report structural configuration status separately from live verified
   operational milestones. Never echo secrets or pretend a connection exists.

## Decision
Choose option 2. Add a pure `checkOutlookActivationReadiness(env)` check:
- Checks the presence and basic format of required server-only bindings and D1.
- Returns required/missing *names*, never values.
- Reports `microsoft_registration_verified`,
  `access_policy_verified`, `migrations_verified`,
  `real_user_consent_verified` and `production_collection_active`
  as **false** until they have separate independently verified evidence.
- Must not be used on its own to mount the OAuth HTTP route or enable cron.
- No change to runtime deployment or existing Worker handlers.

## Follow-up verification gates
1. Operator-controlled Cloudflare Access application and explicit verified
   subject allowlist, with JWT validation and trusted session continuity.
2. Microsoft Entra app registration with HTTPS redirect URI and delegated
   Mail.Read, User.Read, offline_access consent; correct account audience.
3. D1 migrations 003-005 on an explicitly approved test database.
4. End-to-end callback and actual identity verification with the owner present.
5. First Graph Delta run, independent count/link comparison and data retention review.
6. Scheduled runs and monitoring; only then consider enabling a production
   availability indicator. Purchase capability remains excluded.

## Reversibility and proof
Additive pure module and tests. CI covers no secret disclosure and
fail-closed missing config. Existing main and deployed app stay untouched.
