// Cloudflare Worker HTTP routing boundary for Microsoft consent.
// A second explicit switch is required before mounting authorization routes.
// No connection to the scheduled collector or public app is inferred.
import {createAccessProtectedOutlookConsent} from "./leboncoin-access-consent.mjs";
import {handleOutlookManualSync} from "./leboncoin-manual-sync.mjs";
import {handleOutlookReadiness} from "./leboncoin-readiness-http.mjs";

const HIDDEN={"Cache-Control":"no-store, private","Referrer-Policy":"no-referrer"};
const ROUTES=new Set(["/auth/microsoft/start","/auth/microsoft/callback"]);
export async function handleOutlookWorkerRoute({request,env,fetchImpl=fetch}) {
  const path=new URL(request.url).pathname;
  if(path==="/internal/outlook/readiness")return handleOutlookReadiness({request,env,fetchImpl});
  if(path==="/internal/outlook/sync")return handleOutlookManualSync({request,env,fetchImpl});
  if(!ROUTES.has(path))return null;
  // Do not initialize credentials, touch D1, contact Access or Microsoft
  // until BOTH opt-in flags are explicitly enabled by the operator.
  if(env?.OUTLOOK_ROUTES_ENABLED!=="true" || env?.OUTLOOK_CONSENT_ENABLED!=="true")
    return new Response(JSON.stringify({error:"not_found"}),{
      status:404,headers:{...HIDDEN,"Content-Type":"application/json; charset=utf-8"}});
  // Failed configuration must not expose internal environment names publicly.
  try {
    const handler=createAccessProtectedOutlookConsent({env,fetchImpl});
    return await handler(request);
  } catch(error) {
    // Fail closed on invalid Access identity or missing private bindings,
    // but do not expose the origin, secret names or underlying error details.
    return new Response(JSON.stringify({error:"not_found"}),{
      status:404,headers:{...HIDDEN,"Content-Type":"application/json; charset=utf-8"}});
  }
}
