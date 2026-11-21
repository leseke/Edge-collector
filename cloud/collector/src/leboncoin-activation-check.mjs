// Readiness diagnostics: return boolean configuration states, never secret values.
// Offline-safe: no Microsoft, Cloudflare, D1, or mailbox request.
const required=[
  "OUTLOOK_CLIENT_ID","OUTLOOK_CLIENT_SECRET","OUTLOOK_REDIRECT_URI",
  "OUTLOOK_ENCRYPTION_KEY","OUTLOOK_DELTA_ENCRYPTION_KEY","CF_ACCESS_TEAM_DOMAIN","CF_ACCESS_APP_AUD",
  "CF_ACCESS_ALLOWED_SUBJECTS","OUTLOOK_ALLOWED_SENDER_DOMAINS"
];
const validate=(key,val)=>{
  if(typeof val!=="string" || !val.trim())return false;
  if(key==="OUTLOOK_CLIENT_ID")return /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(val);
  if(key==="OUTLOOK_ENCRYPTION_KEY" || key==="OUTLOOK_DELTA_ENCRYPTION_KEY")return /^[a-f0-9]{64}$/i.test(val);
  if(key==="OUTLOOK_ALLOWED_SENDER_DOMAINS")return val.length<=512 && val.split(",").every(v=>/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$/.test(v.trim().toLowerCase()));
  if(key==="CF_ACCESS_ALLOWED_SUBJECTS")return val.split(",").filter(Boolean).length===1 && val.length<256;
  if(key==="OUTLOOK_REDIRECT_URI" || key==="CF_ACCESS_TEAM_DOMAIN"){
    try{
      const url=new URL(val);
      return url.protocol==="https:" && !url.username && !url.password &&
        !url.search && !url.hash &&
        (key!=="CF_ACCESS_TEAM_DOMAIN" || /^[a-z0-9-]+\.cloudflareaccess\.com$/.test(url.hostname));
    }catch{return false}
  }
  return val.length<2048;
};
export function checkOutlookActivationReadiness(env={}) {
  // Never echo the content of environment variables.
  const configuration=Object.fromEntries(required.map(k=>[k,validate(k,env[k])]));
  const missing=required.filter(k=>!configuration[k]);
  const d1=Boolean(env.DB && typeof env.DB.prepare==="function" && typeof env.DB.batch==="function");
  const consentEnabled=env.OUTLOOK_CONSENT_ENABLED==="true";
  const routesEnabled=env.OUTLOOK_ROUTES_ENABLED==="true";
  // Credential provision is a separate explicit operator-approved step.
  return {
    configured:missing.length===0 && d1,
    enabled:consentEnabled,
    ready_for_live_consent:missing.length===0 && d1 && consentEnabled && routesEnabled,
    missing_or_invalid_bindings:missing,
    database_binding_present:d1,
    // These require externally verified facts: do not infer from config names.
    access_policy_verified:false,
    microsoft_registration_verified:false,
    migrations_verified:false,
    real_user_consent_verified:false,
    production_collection_active:false
  };
}
