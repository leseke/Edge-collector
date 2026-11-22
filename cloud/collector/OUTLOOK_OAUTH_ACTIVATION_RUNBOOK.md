# EDGE Outlook — Microsoft OAuth activation gates (2026-11-22)

**Status: preparation only. No OAuth routes, Microsoft consent, mailbox imports, or scheduling are authorized here.** Deployment of the D1 binding was independently confirmed through the operator's successful GitHub Actions run.

## Exact application settings to verify

- Microsoft Entra application: single-account owner-controlled registration supporting **personal Microsoft accounts**.
- Platform: **Web** (server-side confidential authorization-code client, not SPA).
- Registered redirect URI (exact match, case-sensitive):
  `https://edge-outlook-collector.ylan-seke.workers.dev/auth/microsoft/callback`
- Microsoft authorization authority for personal Outlook: `https://login.microsoftonline.com/consumers` (registration account types must support that audience).
- Delegated permissions: `Mail.Read`, `User.Read`, `offline_access`; no application-wide `Mail.Read` permission, no implicit grant, no broad Graph administrator consent.
- Use authorization code + PKCE, verify state/session, and verify account identity before encrypted token persistence.
- The Cloudflare Access login via email/One-time PIN and Microsoft OAuth consent are **distinct**: logging into Access never grants Microsoft Graph permission.

## Cloudflare Access app verification — require all before activation

- Access app hostname exactly `edge-outlook-collector.ylan-seke.workers.dev`; rule `EDGE Outlook - Owner Only` allows only the operator's exact email address.
- Obtain Access app **AUD tag** from its configuration; obtain team domain from Access (previous login displayed `royal-frog-df5c.cloudflareaccess.com`, but independently verify it in Zero Trust rather than guessing).
- Obtain the JWT **subject** (`sub`) by a dedicated authenticated diagnostic that verifies the signature/issuer/audience first; never guess `sub` from an email, name or browser header.
- Test unauthorized requests and ensure Access challenges them. Then use a deliberately staged, reviewed read-only endpoint to verify that Access JWT validation succeeds; do not enable all routes to test identity.
- Cloudflare Access must cover the OAuth start AND callback route, preserving the same verified owner session for both. Microsoft will redirect the browser back; never use OAuth tokens in the URL response body.

## Secret handling and phases

The following belong to **Cloudflare Worker secrets**, never GitHub source files or public variables:
`OUTLOOK_CLIENT_SECRET`, `OUTLOOK_ENCRYPTION_KEY`,
`OUTLOOK_DELTA_ENCRYPTION_KEY`, `CF_ACCESS_ALLOWED_SUBJECTS`.
The client ID, pinned redirect URI, tenant authority, app audience/team domain and sender allowlist are non-secret but security-sensitive configuration; do not invent any values.

The currently published staged Wrangler config sets ALL of
`OUTLOOK_ROUTES_ENABLED`, `OUTLOOK_CONSENT_ENABLED`,
`OUTLOOK_INGEST_ENABLED`, `OUTLOOK_MANUAL_SYNC_ENABLED`,
`OUTLOOK_OFFERS_ENABLED`, `OUTLOOK_DIAGNOSTICS_ENABLED`,
`OUTLOOK_SCHEDULE_ENABLED` to `false`.
Any activation must be a **new**, separately reviewed, single-purpose workflow with exact-branch authorization and a successful disabled-mode rollback plan. Do not reuse the bootstrap or D1 migration workflows for OAuth.

### Recommended release gates

1. Entra registration/supported-account type/redirect/permission review (no token exchanges).
2. Cloudflare Access JWT/audience/operator subject verification with read-only diagnostics.
3. Provision secrets using the **secrets** API/Cloudflare console and verify configured-vs-missing flags without echoing any value.
4. Explicitly enable only OAuth routes and consent after separate owner approval, verify first login + callback; keep Graph ingestion and scheduling disabled.
5. Verify encrypted credential storage, mailbox identity, no duplicate state consumption, and revocation/refresh behavior.
6. Only after successful consent, separately approve one small real-message test with sender allowlist and deduplication; schedule a recurring collection as the final step.

## Encryption-key provisioning (not activated)

Implementation checked: `cloud/collector/src/leboncoin-oauth-store.mjs` and
`cloud/collector/src/leboncoin-delta-store.mjs` each require a **64-character
hexadecimal string** (32 cryptographically random bytes) imported into WebCrypto
AES-256-GCM. Do not use ordinary passwords, hand-typed hex digits, UUIDs,
Microsoft client secrets, or the same key for both purposes.

The owner must generate two independent values with an OS cryptographic random
generator or reputable password manager that supports 32 random bytes as hex.
Store a recovery copy of each secret in a trusted encrypted password manager:
if encrypted records are written and the key is irretrievably lost, those
records cannot be decrypted. Never paste key values into issues, pull requests,
workflow outputs, logs, chat, screenshots, or `wrangler.jsonc`.

Add to Cloudflare production Worker `edge-outlook-collector` > Settings >
Variables and Secrets as **Secret** bindings:

- `OUTLOOK_ENCRYPTION_KEY` — 32 random bytes, encoded as 64 hex characters.
- `OUTLOOK_DELTA_ENCRYPTION_KEY` — a separately generated 32-byte value.

Before creating a secret, check its name is not already present.
**Do not overwrite an existing key** without a deliberate migration and
re-encryption procedure. Do not delete or overwrite `OUTLOOK_CLIENT_SECRET`.
Changing a Worker secret can create/deploy a new Worker version, so confirm
the D1 binding, Cloudflare Access protection and seven disabled flags remain
unchanged after every secret update.

Do not generate encryption keys in this repository or GitHub Actions as part
of routine deployments: neither an accidental rotation nor an inaccessible
recovery key is acceptable. The secure provisioning itself is an operator
action and requires an independent verification of existence (name/type only).

## Cloudflare Access AUD naming and first-owner identity bootstrap

The operator configured `CF_ACCESS_AUD` through the Cloudflare UI.
The runtime previously required `CF_ACCESS_APP_AUD`. Both names are now
supported through `resolveCloudflareAccessAudience()`, but two different
values deliberately fail closed. Do **not** copy an incomplete/truncated AUD
from screenshots into Wrangler or logs. Never configure an invented value.

The Cloudflare Access team domain is now staged in Wrangler as the exact
HTTPS URL `https://royal-frog-df5c.cloudflareaccess.com` — the JWT verifier
requires this URL form, not the bare hostname. The redirect URI and Microsoft
consumer authority are likewise staged, while all seven enable flags remain
`false`. Review these nonsecret values against the Cloudflare and Entra
dashboards before any redeploy. Since dashboard changes may create a new
Worker version, review live bindings and secret presence independently.

### First-owner `sub` discovery is not yet implemented or deployed

The existing `/internal/outlook/readiness` endpoint is intentionally
allowlist-protected and cannot discover an unknown initial `sub`: it
requires `CF_ACCESS_ALLOWED_SUBJECTS` first. Never claim it can bootstrap
the first subject or bypass this guard.

A separately authorized bootstrap may verify a **real** Cloudflare Access
JWT's RS256 signature, `iss`, `aud`, timestamps and `type=app`
against the pinned issuer JWKS; only then retrieve the opaque `sub` over
the authenticated owner's Access-protected browser session. It must have an
independent, default-off, one-time activation gate and no Microsoft OAuth,
mailbox or D1 writes. It must never return full JWTs, cookies, raw provider
tokens or keys, and must be disabled immediately after setting the exact
`CF_ACCESS_ALLOWED_SUBJECTS` Worker **Secret**. This bootstrap is **not**
part of the current release and must be reviewed/tested independently
before deploying.

## Production safety

Do not modify `main`, the existing TCG worker/database, or the public application. Do not ask the operator to paste a client secret, access token, refresh token, PKCE verifier or one-time password in chat.

References:
- https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow
- https://learn.microsoft.com/en-us/entra/identity-platform/reply-url
- https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/
