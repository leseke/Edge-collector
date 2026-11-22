// Development assembly only, intentionally NOT mounted on a deployed route.
// Cloudflare Access must gate traffic AND its signed application JWT is
// independently validated before EDGE owner-specific Microsoft consent.
import { verifyCloudflareAccessSession } from "./leboncoin-access-session.mjs";
import { resolveCloudflareAccessAudience } from "./leboncoin-access-audience.mjs";
import { createD1OAuthStores } from "./leboncoin-oauth-store.mjs";
import { createOutlookConsentHandler } from "./leboncoin-consent-http.mjs";

export function createAccessProtectedOutlookConsent({env,fetchImpl=fetch}) {
  const audience=resolveCloudflareAccessAudience(env);
  if (!env?.DB || !env?.OUTLOOK_ENCRYPTION_KEY || !env?.CF_ACCESS_TEAM_DOMAIN ||
      !audience || !env?.OUTLOOK_CLIENT_ID ||
      !env?.OUTLOOK_CLIENT_SECRET || !env?.OUTLOOK_REDIRECT_URI ||
      !env?.CF_ACCESS_ALLOWED_SUBJECTS)
    throw new Error("missing_outlook_consent_config");
  // A misconfigured OAuth redirect must never send authorization codes to
  // another Worker, a preview host, or the public EDGE application.
  // This check is independent of the Entra registration and fails closed.
  const expectedRedirect="https://edge-outlook-collector.ylan-seke.workers.dev/auth/microsoft/callback";
  if(env.OUTLOOK_REDIRECT_URI!==expectedRedirect)
    throw new Error("invalid_outlook_redirect_uri");
  const allowedSubjects=env.CF_ACCESS_ALLOWED_SUBJECTS.split(",").map(s=>s.trim()).filter(Boolean);
  if(allowedSubjects.length!==1)throw new Error("operator_allowlist_required");
  return createOutlookConsentHandler({
    enabled:env.OUTLOOK_CONSENT_ENABLED==="true",
    redirectUri:env.OUTLOOK_REDIRECT_URI,
    tenant:env.OUTLOOK_TENANT || "consumers",
    clientId:env.OUTLOOK_CLIENT_ID,clientSecret:env.OUTLOOK_CLIENT_SECRET,
    fetchImpl,
    verifySession:request=>verifyCloudflareAccessSession(request,{
      teamUrl:env.CF_ACCESS_TEAM_DOMAIN,
      audience,allowedSubjects,fetchImpl
    }),
    getStores:session=>createD1OAuthStores({
      db:env.DB,mailboxKey:session.ownerKey,encryptionKey:env.OUTLOOK_ENCRYPTION_KEY
    })
  });
}
