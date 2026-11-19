# ADR 020 — Operator authentication with Cloudflare Access JWT

Status: DEVELOPMENT, not mounted or deployed. Date: 2026-11-19.

## Context
EDGE has no verified user login/session system for OAuth consent. Merely trusting
an email header, an unverified JWT payload, or an app-wide shared key would
allow the wrong person to connect an Outlook mailbox or gain access to its
refresh token. A trusted authenticated principal is required *before* enabling
`/auth/microsoft/start` or `/auth/microsoft/callback`.

## Alternatives
1. Create a custom login/password and persistent account/session stack.
   Adds credential-reset, MFA, session, brute-force and recovery duties.
2. Reuse Cloudflare Access policies for single-operator sign-in and validate
   the Access application JWT cryptographically in the Worker.
3. Trust only Cloudflare-added email/user headers without JWT verification.
   Reject: upstream routing or proxy misconfiguration could make it spoofable.

## Decision
Choose option 2 for an initial single-operator implementation, contingent
on separately provisioning a Cloudflare Access application:
- `leboncoin-access-session.mjs`: accept only a signed Access application
  JWT from `Cf-Access-Jwt-Assertion`. Verify RS256 against the team's pinned
  certificates endpoint, exact issuer, application audience, exp, iat, type,
  and allowlisted `sub`. Do not trust email header or unsigned claims.
- Derive a stable opaque ownerKey from issuer, audience, subject; derive a
  consent session ID from the token hash, binding start and callback to
  the same Access session. Sessions may rotate during consent: restart
  required rather than weakening verification.
- `leboncoin-access-consent.mjs`: inject the verified identity into the
  previously disabled OAuth consent HTTP adapter and encrypted D1 stores.
- Require exactly one explicitly allowlisted subject. JWT verification
  is necessary but does not replace the Access perimeter policy.

## Runtime and threat boundaries
- **Not mounted** on any deployed Worker route. No Cloudflare Access
  application, Microsoft Entra app or D1 secret provisioning performed.
- `CF_ACCESS_TEAM_DOMAIN` must be the exact HTTPS Cloudflare Access team
  domain; `CF_ACCESS_APP_AUD` must be the correct app AUD.
- `CF_ACCESS_ALLOWED_SUBJECTS` must be a carefully verified trusted subject
  identifier from a real Access token, configured server-side. Never accept
  this value from a request header/query.
- Access uses application audience claims and `Cf-Access-Jwt-Assertion` JWT,
  not a generic Microsoft login or ChatGPT connector grant.
- Fetch JWK only from pinned team origin, enforce reasonable response size,
  timeout, key rotation/caching and rate limits before enabling publicly.
  A replayed signed Access JWT remains usable until expiry unless additional
  anti-replay controls are introduced for privileged operations.
- Avoid cached operator identity or credential values in frontend or CI.
- Introduce a production-safe OAuth reconnect/disconnect UX, mailbox
  identity confirmation, approval and audit trail prior to activation.

## CI / done criterion
Offline tests sign a real RSA key and validate accepted JWT, signature
corruption, invalid issuer/audience/subject/type/expiry, disabled endpoint,
missing secrets and allowlist. CI required for acceptance.

## Reversibility
Standalone, additive files on a development branch only. The original
application and production paths are unchanged.
