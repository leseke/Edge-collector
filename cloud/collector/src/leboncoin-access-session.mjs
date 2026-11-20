// Strict Cloudflare Access application JWT verifier for EDGE operator sessions.
// This is an integration adapter, not a provisioned Access policy or public route.
// Never authorize via unverified cf-access headers, email or unsigned JWT claims.
const enc=new TextEncoder(),dec=new TextDecoder();
const b64dec=s=>Uint8Array.from(atob(s.replace(/-/g,"+").replace(/_/g,"/")+"=".repeat((4-s.length%4)%4)),x=>x.charCodeAt(0));
const b64enc=bytes=>btoa(String.fromCharCode(...bytes)).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/g,"");
const hash=async data=>b64enc(new Uint8Array(await crypto.subtle.digest("SHA-256",enc.encode(data))));
const fail=()=>{throw new Error("invalid_access_identity")};
function parseJsonPart(str) {
  if(typeof str!=="string" || str.length>10000 || !/^[A-Za-z0-9_-]+$/.test(str))fail();
  try{return JSON.parse(dec.decode(b64dec(str)))}catch{fail()}
}
function teamDomain(value) {
  if(typeof value!=="string")fail();
  try {
    const u=new URL(value);
    if(u.protocol!=="https:" || u.username || u.password || u.port ||
       u.pathname!=="/" || u.search || u.hash ||
       !/^[a-z0-9-]+\.cloudflareaccess\.com$/.test(u.hostname))fail();
    return u.origin;
  } catch {fail()}
}
export async function deriveCloudflareAccessOwnerKey({teamUrl,audience,subject}) {
  const issuer=teamDomain(teamUrl);
  if(typeof audience!=="string" || !/^[A-Za-z0-9_-]{8,128}$/.test(audience) ||
     typeof subject!=="string" || !subject || subject.length>256)fail();
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",
    enc.encode(issuer+"|"+audience+"|"+subject)))).map(x=>x.toString(16).padStart(2,"0")).join("");
}
export async function verifyCloudflareAccessSession(request,{
  teamUrl,audience,allowedSubjects,fetchImpl=fetch,clock=()=>Date.now()
}) {
  const issuer=teamDomain(teamUrl);
  if(typeof audience!=="string" || !/^[A-Za-z0-9_-]{8,128}$/.test(audience) ||
     !Array.isArray(allowedSubjects) || allowedSubjects.length===0 ||
     !allowedSubjects.every(x=>typeof x==="string" && x.length>0))fail();
  const token=request.headers.get("Cf-Access-Jwt-Assertion");
  if(!token || token.length>20000)fail();
  const parts=token.split(".");
  if(parts.length!==3)fail();
  const [h,p,sig]=parts;
  const header=parseJsonPart(h),payload=parseJsonPart(p);
  if(header.alg!=="RS256" || typeof header.kid!=="string" ||
     !/^[A-Za-z0-9_-]{1,256}$/.test(header.kid) ||
     payload.iss!==issuer || ![payload.aud].flat().includes(audience) ||
     typeof payload.sub!=="string" || !allowedSubjects.includes(payload.sub) ||
     payload.type!=="app")fail();
  const now=Math.floor(clock()/1000);
  if(!Number.isInteger(payload.exp) || payload.exp<=now ||
     !Number.isInteger(payload.iat) || payload.iat>now+60 ||
     (payload.nbf!==undefined && (!Number.isInteger(payload.nbf) || payload.nbf>now+60)))fail();
  let response;
  try {
    response=await fetchImpl(issuer+"/cdn-cgi/access/certs",{
      method:"GET",redirect:"error",headers:{Accept:"application/json"}
    });
    if(!response.ok)fail();
  }catch{fail()}
  let jwks;
  try {jwks=await response.json()}catch{fail()}
  // Cloudflare also returns a 'keys' array. Do not accept arbitrary issuer
  // URLs or trust an embedded JWK supplied by the caller.
  const candidates=jwks?.keys;
  if(!Array.isArray(candidates) || candidates.length>20)fail();
  const jwk=candidates.find(k=>k.kid===header.kid && k.kty==="RSA" &&
    k.alg==="RS256" && (!k.use || k.use==="sig") &&
    typeof k.n==="string" && typeof k.e==="string");
  if(!jwk)fail();
  try {
    const key=await crypto.subtle.importKey("jwk",jwk,{
      name:"RSASSA-PKCS1-v1_5",hash:"SHA-256"
    },false,["verify"]);
    if(!await crypto.subtle.verify("RSASSA-PKCS1-v1_5",key,b64dec(sig),enc.encode(h+"."+p)))fail();
  } catch {fail()}
  // An authenticated Cloudflare identity_nonce is a signed identity cache
  // key. Prefer it over the entire JWT so a token reissue retaining the
  // identity session does not invalidate the OAuth callback. A changed
  // nonce still fails closed; absent nonce retains strict JWT binding.
  if(payload.identity_nonce!==undefined &&
     (typeof payload.identity_nonce!=="string" ||
      !/^[A-Za-z0-9_-]{8,256}$/.test(payload.identity_nonce)))fail();
  const sessionMaterial=payload.identity_nonce
    ? "access-session|"+issuer+"|"+audience+"|"+payload.sub+"|"+payload.identity_nonce
    : "access-jwt|"+token;
  const sessionId=(await hash(sessionMaterial)).slice(0,64);
  const ownerKey=await deriveCloudflareAccessOwnerKey({teamUrl:issuer,audience,subject:payload.sub});
  return {authenticated:true,sessionId,ownerKey};
}
