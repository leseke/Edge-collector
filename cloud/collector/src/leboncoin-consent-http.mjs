// Development-only OAuth HTTP adapter. NOT mounted by the Cloudflare Worker.
// Required server infrastructure is injected explicitly; never trust a request
// header or user-supplied identity as an authenticated EDGE session.
import { beginMicrosoftConsent, finishMicrosoftConsent } from "./leboncoin-consent.mjs";

const HEADERS={
  "Cache-Control":"no-store, private",
  "Pragma":"no-cache",
  "Referrer-Policy":"no-referrer",
  "X-Content-Type-Options":"nosniff",
  "Content-Security-Policy":"default-src 'none'; frame-ancestors 'none'"
};
const json=(body,status)=>new Response(JSON.stringify(body),{
  status,headers:{...HEADERS,"Content-Type":"application/json; charset=utf-8"}
});
const validatedSession=async (request,verifySession)=>{
  if(typeof verifySession!=="function")throw new Error("missing_trusted_session_verifier");
  const session=await verifySession(request);
  if(!session || session.authenticated!==true ||
      typeof session.sessionId!=="string" ||
      !/^[A-Za-z0-9_-]{16,256}$/.test(session.sessionId))
    return null;
  return session;
};
export function createOutlookConsentHandler({
  enabled=false,redirectUri,tenant="consumers",clientId,clientSecret,
  verifySession,getStores,fetchImpl=fetch
}) {
  return async function handleOutlookConsent(request) {
    const url=new URL(request.url);
    if(!enabled)return json({error:"not_enabled"},404);
    // Block crossorigin, non-HTTPS and unconfigured routes before any token call.
    const expected=new URL(redirectUri);
    if(url.protocol!=="https:" || url.origin!==expected.origin)
      return json({error:"not_found"},404);
    if(request.method!=="GET")return json({error:"method_not_allowed"},405);
    if(url.pathname!=="/auth/microsoft/start" &&
       url.pathname!==expected.pathname)return json({error:"not_found"},404);
    const session=await validatedSession(request,verifySession);
    if(!session)return json({error:"not_authenticated"},401);
    if(typeof getStores!=="function")throw new Error("missing_oauth_store_factory");
    // getStores MUST derive mailboxKey from verified authenticated account
    // context. It must not use callback input or an untrusted HTTP header.
    const stores=await getStores(session);
    if(!stores?.pendingStore || !stores?.credentialStore)
      throw new Error("missing_oauth_stores");

    if(url.pathname==="/auth/microsoft/start") {
      if(url.search)return json({error:"unexpected_parameters"},400);
      const started=await beginMicrosoftConsent({
        tenant,clientId,redirectUri,sessionId:session.sessionId,
        pendingStore:stores.pendingStore
      });
      return new Response(null,{status:302,headers:{...HEADERS,
        "Location":started.authorizationUrl}});
    }
    if(url.searchParams.has("error"))return json({error:"microsoft_authorization_rejected"},400);
    const entries=[...url.searchParams.keys()];
    if(entries.length!==2 || !entries.includes("code") || !entries.includes("state") ||
        url.searchParams.getAll("code").length!==1 ||
        url.searchParams.getAll("state").length!==1)
      return json({error:"invalid_callback_parameters"},400);
    try {
      await finishMicrosoftConsent({tenant,clientId,clientSecret,redirectUri,
        sessionId:session.sessionId,code:url.searchParams.get("code"),
        state:url.searchParams.get("state"),pendingStore:stores.pendingStore,
        credentialStore:stores.credentialStore,fetchImpl});
      // No token or mailbox metadata returned to browser.
      return json({connected:true},200);
    } catch (error) {
      const reason=error instanceof Error?error.message:"unexpected";
      if(reason==="oauth_state_expired_or_replayed" || reason==="oauth_state_mismatch")
        return json({error:"consent_session_invalid"},400);
      // Never return provider response details or credential values.
      return json({error:"microsoft_connection_failed"},502);
    }
  };
}
