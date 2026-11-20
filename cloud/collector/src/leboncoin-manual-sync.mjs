// Explicit operator-triggered Outlook sync. Disabled unless ALL server-side
// opt-ins are true. No user-supplied owner key, cursor or mailbox identifier.
import {verifyCloudflareAccessSession} from "./leboncoin-access-session.mjs";
import {runOutlookLeboncoinCollection} from "./leboncoin-runner.mjs";

const response=(value,status)=>new Response(JSON.stringify(value),{status,headers:{
  "Content-Type":"application/json; charset=utf-8",
  "Cache-Control":"no-store, private",
  "Pragma":"no-cache",
  "Referrer-Policy":"no-referrer",
  "X-Content-Type-Options":"nosniff"
}});
const notFound=()=>response({error:"not_found"},404);
const UUID=/^[0-9a-f]{64}$/i;
export async function handleOutlookManualSync({
  request,env,fetchImpl=fetch,
  verifySession=verifyCloudflareAccessSession,
  runCollection=runOutlookLeboncoinCollection
}) {
  if(new URL(request.url).pathname!=="/internal/outlook/sync")return null;
  if(env?.OUTLOOK_ROUTES_ENABLED!=="true" ||
     env?.OUTLOOK_CONSENT_ENABLED!=="true" ||
     env?.OUTLOOK_INGEST_ENABLED!=="true" ||
     env?.OUTLOOK_MANUAL_SYNC_ENABLED!=="true")return notFound();
  if(request.method!=="POST")return notFound();
  // This endpoint is for same-origin, authenticated operator actions only;
  // unlike a cookie-authenticated form, cross-site POST requests are denied.
  let expected;
  try {expected=new URL(env.OUTLOOK_REDIRECT_URI)} catch{return notFound()}
  const target=new URL(request.url);
  if(target.protocol!=="https:" || expected.protocol!=="https:" ||
     target.origin!==expected.origin ||
     request.headers.get("Origin")!==target.origin ||
     request.headers.get("Content-Type")!=="application/json" ||
     request.headers.get("Sec-Fetch-Site") === "cross-site" ||
     target.search || request.headers.get("Authorization") ||
     request.headers.get("X-Owner-Key"))return notFound();
  // No externally supplied parameters, data, query, cursor or maxPages.
  // Request body is required to be empty JSON to prevent hidden options.
  const body=await request.text();
  if(body.length>2 || body!=="{}")return notFound();
  const allowedSubjects=env.CF_ACCESS_ALLOWED_SUBJECTS?.split(",").map(s=>s.trim()).filter(Boolean);
  if(allowedSubjects?.length!==1 || !env.CF_ACCESS_TEAM_DOMAIN || !env.CF_ACCESS_APP_AUD)
    return notFound();
  let identity;
  try {
    identity=await verifySession(request,{
      teamUrl:env.CF_ACCESS_TEAM_DOMAIN,
      audience:env.CF_ACCESS_APP_AUD,allowedSubjects,fetchImpl
    });
  } catch{return notFound()}
  if(identity?.authenticated!==true || !UUID.test(identity.ownerKey||""))
    return notFound();
  try {
    const result=await runCollection({
      env,ownerKey:identity.ownerKey,fetchImpl,maxPages:3
    });
    if(result?.status==="BUSY")return response({status:"BUSY"},409);
    return response({status:result.status,complete:result.complete===true,
      pages:result.pages??0,messages_scanned:result.messages_scanned??0,
      matching_alerts:result.matching_alerts??0,
      inserted_listings:result.inserted_listings??0,
      already_seen_messages:result.already_seen_messages??0},200);
  } catch {
    // Never send provider errors, mailbox IDs, secrets or refresh tokens
    // to clients. Error categorization is internal and requires monitoring.
    return response({status:"FAILED"},503);
  }
}
