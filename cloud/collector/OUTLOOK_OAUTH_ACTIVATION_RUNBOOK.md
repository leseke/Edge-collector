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

## Production safety

Do not modify `main`, the existing TCG worker/database, or the public application. Do not ask the operator to paste a client secret, access token, refresh token, PKCE verifier or one-time password in chat.

References:
- https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow
- https://learn.microsoft.com/en-us/entra/identity-platform/reply-url
- https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/
