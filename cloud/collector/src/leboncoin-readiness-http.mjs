// Operator-only, read-only Outlook activation diagnostics.
// No D1 SQL, Graph, Azure or Cloudflare management requests. Missing external
// verification is explicitly UNKNOWN, not inferred from environment variables.
import {verifyCloudflareAccessSession} from "./leboncoin-access-session.mjs";
import {resolveCloudflareAccessAudience} from "./leboncoin-access-audience.mjs";
import {checkOutlookActivationReadiness} from "./leboncoin-activation-check.mjs";
const privateJson=(body,status)=>new Response(JSON.stringify(body),{
  status,headers:{"Content-Type":"application/json; charset=utf-8",
    "Cache-Control":"no-store, private","Pragma":"no-cache",
    "Referrer-Policy":"no-referrer","X-Content-Type-Options":"nosniff"}
});
const hidden=()=>privateJson({error:"not_found"},404);
export async function handleOutlookReadiness({
  request,env,fetchImpl=fetch,verifySession=verifyCloudflareAccessSession
}){
  const url=new URL(request.url);
  if(url.pathname!=="/internal/outlook/readiness")return null;
  if(env?.OUTLOOK_ROUTES_ENABLED!=="true" ||
     env?.OUTLOOK_DIAGNOSTICS_ENABLED!=="true")return hidden();
  if(request.method!=="GET" || url.search || url.hash ||
     url.protocol!=="https:" || request.headers.has("Authorization") ||
     request.headers.has("X-Owner-Key"))return hidden();
  let expected;
  try{expected=new URL(env.OUTLOOK_REDIRECT_URI)}catch{return hidden()}
  if(expected.protocol!=="https:" || url.origin!==expected.origin)return hidden();
  const subjects=typeof env.CF_ACCESS_ALLOWED_SUBJECTS==="string"
    ?env.CF_ACCESS_ALLOWED_SUBJECTS.split(",").map(x=>x.trim()).filter(Boolean):[];
  const audience=resolveCloudflareAccessAudience(env);
  if(subjects.length!==1 || !env.CF_ACCESS_TEAM_DOMAIN || !audience)
    return hidden();
  try{
    const identity=await verifySession(request,{
      teamUrl:env.CF_ACCESS_TEAM_DOMAIN,
      audience,
      allowedSubjects:subjects,fetchImpl
    });
    if(identity?.authenticated!==true || !/^[0-9a-f]{64}$/i.test(identity.ownerKey||""))
      return hidden();
  }catch{return hidden()}
  // This is ONLY a shape check. Do not run SQL or inspect tokens/rows.
  const readiness=checkOutlookActivationReadiness(env);
  const switches={
    routes:env.OUTLOOK_ROUTES_ENABLED==="true",
    consent:env.OUTLOOK_CONSENT_ENABLED==="true",
    manual_sync:env.OUTLOOK_MANUAL_SYNC_ENABLED==="true",
    ingest:env.OUTLOOK_INGEST_ENABLED==="true",
    scheduled:env.OUTLOOK_SCHEDULE_ENABLED==="true"
  };
  return privateJson({
    status:"CONFIGURATION_ONLY_NOT_LIVE_VERIFIED",
    configured:readiness.configured,
    ready_for_live_consent:readiness.ready_for_live_consent,
    switches,
    database_binding_present:readiness.database_binding_present,
    missing_or_invalid_bindings:readiness.missing_or_invalid_bindings,
    external_verification:{
      microsoft_registration:"NOT_VERIFIED",
      cloudflare_access_policy:"NOT_VERIFIED",
      remote_d1_migrations:"NOT_VERIFIED",
      independent_user_consent:"NOT_VERIFIED",
      production_collection:"NOT_VERIFIED"
    }
  },200);
}
