// Confidential Microsoft OAuth authorization-code + PKCE preparation.
// Host app supplies: authenticated sessionId, atomic one-use pendingStore,
// HTTPS callback URI, private client secret and encrypted credentialStore.
// No routes are made public by this module.
const encoder = new TextEncoder();
const ALLOWED_TENANTS = /^(?:consumers|organizations|common|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/i;
const CLIENT_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const B64URL = value => btoa(String.fromCharCode(...value)).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/g,"");
const random = n => B64URL(crypto.getRandomValues(new Uint8Array(n)));
const hash = async s => B64URL(new Uint8Array(await crypto.subtle.digest("SHA-256",encoder.encode(s))));
function config({tenant="consumers",clientId,redirectUri}) {
  if (!ALLOWED_TENANTS.test(tenant) || !CLIENT_ID.test(clientId || ""))
    throw new Error("invalid_microsoft_oauth_config");
  let callback;
  try {callback=new URL(redirectUri)} catch {throw new Error("invalid_microsoft_redirect_uri")}
  if (callback.protocol!=="https:" || callback.username || callback.password ||
      callback.hash || callback.search || !callback.hostname ||
      callback.hostname==="localhost" || callback.hostname==="127.0.0.1")
    throw new Error("invalid_microsoft_redirect_uri");
  return {tenant,clientId,redirectUri:callback.toString()};
}
const ensureStore = s => {
  if (!s || typeof s.create!=="function" || typeof s.consume!=="function")
    throw new Error("missing_atomic_oauth_pending_store");
};
const ensureSession = sessionId => {
  if (typeof sessionId!=="string" || !/^[a-zA-Z0-9_-]{16,256}$/.test(sessionId))
    throw new Error("invalid_oauth_session");
};

// pendingStore.create({stateHash,sessionHash,verifier,redirectUri,expiresAt})
// must enforce stateHash uniqueness, TTL and secret-at-rest encryption.
// pendingStore.consume(stateHash) MUST atomically delete and return once.
export async function beginMicrosoftConsent({tenant="consumers",clientId,redirectUri,
  sessionId,pendingStore,now=()=>Date.now()}) {
  const c=config({tenant,clientId,redirectUri});
  ensureSession(sessionId);ensureStore(pendingStore);
  const state=random(32), verifier=random(48);
  const challenge=await hash(verifier), stateHash=await hash(state), sessionHash=await hash(sessionId);
  const expiresAt=now()+10*60_000;
  await pendingStore.create({stateHash,sessionHash,verifier,redirectUri:c.redirectUri,expiresAt});
  const url=new URL("https://login.microsoftonline.com/"+c.tenant+"/oauth2/v2.0/authorize");
  url.searchParams.set("client_id",c.clientId);
  url.searchParams.set("response_type","code");
  url.searchParams.set("redirect_uri",c.redirectUri);
  url.searchParams.set("response_mode","query");
  url.searchParams.set("scope","offline_access Mail.Read");
  url.searchParams.set("state",state);
  url.searchParams.set("code_challenge",challenge);
  url.searchParams.set("code_challenge_method","S256");
  return {authorizationUrl:url.toString(),expiresAt};
}

export async function finishMicrosoftConsent({tenant="consumers",clientId,clientSecret,redirectUri,
  sessionId,state,code,pendingStore,credentialStore,verifyIdentity,fetchImpl=fetch,now=()=>Date.now()}) {
  const c=config({tenant,clientId,redirectUri});
  ensureSession(sessionId);ensureStore(pendingStore);
  if (!credentialStore || typeof credentialStore.save!=="function")
    throw new Error("missing_secure_credential_store");
  if (typeof clientSecret!=="string" || !clientSecret || typeof state!=="string" ||
      !/^[A-Za-z0-9_-]{40,128}$/.test(state) || typeof code!=="string" ||
      code.length<8 || code.length>8192) throw new Error("invalid_oauth_callback");
  const pending=await pendingStore.consume(await hash(state));
  if (!pending) throw new Error("oauth_state_expired_or_replayed");
  // fail closed after consuming an invalid transaction; never allow replay.
  if (pending.sessionHash!==await hash(sessionId) || pending.redirectUri!==c.redirectUri ||
      !Number.isFinite(pending.expiresAt) || pending.expiresAt<now() ||
      typeof pending.verifier!=="string" || !/^[A-Za-z0-9_-]{43,128}$/.test(pending.verifier))
    throw new Error("oauth_state_mismatch");
  const data=new URLSearchParams({
    client_id:c.clientId,client_secret:clientSecret,grant_type:"authorization_code",
    code,redirect_uri:c.redirectUri,code_verifier:pending.verifier,
    scope:"offline_access Mail.Read"
  });
  const response=await fetchImpl("https://login.microsoftonline.com/"+c.tenant+"/oauth2/v2.0/token",{
    method:"POST",redirect:"error",
    headers:{"Content-Type":"application/x-www-form-urlencoded"},body:data.toString()
  });
  if (!response.ok) throw new Error("microsoft_code_exchange_http_"+response.status);
  const tokens=await response.json();
  if (typeof tokens.access_token!=="string" || !tokens.access_token ||
      typeof tokens.refresh_token!=="string" || !tokens.refresh_token ||
      !Number.isFinite(tokens.expires_in) || tokens.expires_in<=0)
    throw new Error("microsoft_code_exchange_invalid_response");
  // Guarded HTTP integration must inject identity attestation before any save.
  const verified = verifyIdentity ? await verifyIdentity(tokens.access_token) : null;
  if (verifyIdentity && (typeof verified?.accountId !== "string" || !verified.accountId))
    throw new Error("graph_identity_unverified");
  // Never store a mailbox address; persist the verified opaque Graph identity.
  await credentialStore.save(verified ? {refreshToken:tokens.refresh_token,accountId:verified.accountId} : {refreshToken:tokens.refresh_token});
  return {connected:true,expiresInSeconds:tokens.expires_in};
}
