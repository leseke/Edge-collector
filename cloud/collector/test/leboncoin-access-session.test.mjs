import test from "node:test";
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {verifyCloudflareAccessSession} from "../src/leboncoin-access-session.mjs";
import {beginMicrosoftConsent,finishMicrosoftConsent} from "../src/leboncoin-consent.mjs";
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const enc=new TextEncoder();
const b64=bytes=>btoa(String.fromCharCode(...bytes)).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/g,"");
const issuer="https://edge-team.cloudflareaccess.com",audience="edge-audience-1234";
const now=Date.parse("2026-11-19T13:00:00Z");
async function fixture(){
  const pair=await crypto.subtle.generateKey({name:"RSASSA-PKCS1-v1_5",modulusLength:2048,
    publicExponent:new Uint8Array([1,0,1]),hash:"SHA-256"},true,["sign","verify"]);
  const jwk=await crypto.subtle.exportKey("jwk",pair.publicKey);
  const sign=async payload=>{
    const head=b64(enc.encode(JSON.stringify({alg:"RS256",kid:"trusted-key"})));
    const data=b64(enc.encode(JSON.stringify(payload)));
    const sig=await crypto.subtle.sign("RSASSA-PKCS1-v1_5",pair.privateKey,enc.encode(head+"."+data));
    return head+"."+data+"."+b64(new Uint8Array(sig));
  };
  const claims={iss:issuer,aud:audience,sub:"operator-sub-1",type:"app",
    iat:Math.floor(now/1000)-30,exp:Math.floor(now/1000)+3600};
  let certificateRequests=0;
  const fetchImpl=async url=>{
    certificateRequests++;
    assert.equal(url,issuer+"/cdn-cgi/access/certs");
    return {ok:true,json:async()=>({keys:[{...jwk,kid:"trusted-key",alg:"RS256",use:"sig"}]})};
  };
  const args={teamUrl:issuer,audience,allowedSubjects:["operator-sub-1"],clock:()=>now,fetchImpl};
  const verify=async (token,overrides={})=>verifyCloudflareAccessSession(new Request("https://edge.example.com",{
    headers:{"Cf-Access-Jwt-Assertion":token}
  }),{...args,...overrides});
  return {sign,claims,verify,get certificateRequests(){return certificateRequests}};
}
test("valid Cloudflare Access JWT produces stable owner and session-bound nonce",async()=>{
  const f=await fixture();
  const token=await f.sign(f.claims);
  const first=await f.verify(token),second=await f.verify(token);
  assert.equal(first.authenticated,true);
  assert.match(first.ownerKey,/^[0-9a-f]{64}$/);
  assert.equal(first.sessionId,second.sessionId);
  assert.equal(first.ownerKey,second.ownerKey);
  assert.equal(f.certificateRequests,2);
});
test("signed identity nonce survives reissued Access JWT but not a new login",async()=>{
  const f=await fixture();
  const base={...f.claims,identity_nonce:"login-nonce-A1234"};
  const first=await f.verify(await f.sign(base));
  const renewed=await f.verify(await f.sign({...base,iat:base.iat+60,exp:base.exp+60}));
  assert.equal(first.sessionId,renewed.sessionId);
  assert.equal(first.ownerKey,renewed.ownerKey);
  const other=await f.verify(await f.sign({...base,identity_nonce:"login-nonce-B5678"}));
  assert.notEqual(first.sessionId,other.sessionId);
  assert.equal(first.ownerKey,other.ownerKey);
});
test("missing identity nonce keeps strict JWT session binding",async()=>{
  const f=await fixture();
  const first=await f.verify(await f.sign(f.claims));
  const renewed=await f.verify(await f.sign({...f.claims,iat:f.claims.iat+60}));
  assert.notEqual(first.sessionId,renewed.sessionId);
});
test("invalid signed identity nonce is rejected",async()=>{
  const f=await fixture();
  for(const identity_nonce of ["", "short", "../x", 10]){
    await assert.rejects(f.verify(await f.sign({...f.claims,identity_nonce})),/invalid_access_identity/);
  }
});
test("OAuth start and callback accept signed Access JWT reissue with same identity nonce",async()=>{
  const f=await fixture();
  const nonce="signed-login-A12345";
  const claims={...f.claims,identity_nonce:nonce};
  const startSession=await f.verify(await f.sign(claims));
  const callbackSession=await f.verify(await f.sign({...claims,iat:claims.iat+60,exp:claims.exp+60}));
  const pending=new Map();
  const pendingStore={
    async create(x){pending.set(x.stateHash,x)},
    async consume(x){const v=pending.get(x);pending.delete(x);return v??null}
  };
  const redirectUri="https://edge.example.com/auth/microsoft/callback";
  const clientId="123e4567-e89b-12d3-a456-426614174000";
  const nowMillis=now;
  const started=await beginMicrosoftConsent({clientId,redirectUri,
    sessionId:startSession.sessionId,pendingStore,now:()=>nowMillis});
  const state=new URL(started.authorizationUrl).searchParams.get("state");
  const saved=[];
  const completed=await finishMicrosoftConsent({
    clientId,clientSecret:"fixture-client",redirectUri,
    sessionId:callbackSession.sessionId,pendingStore,state,
    code:"fixture-authorization-code",now:()=>nowMillis,
    credentialStore:{save:async entry=>saved.push(entry)},
    verifyIdentity:async()=>({accountId:"graph-account-123"}),
    fetchImpl:async()=>({ok:true,json:async()=>({
      access_token:"access-fixture",refresh_token:"refresh-fixture",expires_in:3600
    })})
  });
  assert.equal(completed.connected,true);
  assert.deepEqual(saved,[{refreshToken:"refresh-fixture",accountId:"graph-account-123"}]);
  assert.equal(pending.size,0);
});
test("OAuth callback refuses a new signed Access identity nonce",async()=>{
  const f=await fixture();
  const claims={...f.claims,identity_nonce:"signed-login-A12345"};
  const first=await f.verify(await f.sign(claims));
  const second=await f.verify(await f.sign({...claims,identity_nonce:"signed-login-B67890"}));
  const pending=new Map(),pendingStore={
    async create(x){pending.set(x.stateHash,x)},
    async consume(x){const v=pending.get(x);pending.delete(x);return v??null}
  };
  const redirectUri="https://edge.example.com/auth/microsoft/callback";
  const clientId="123e4567-e89b-12d3-a456-426614174000";
  const started=await beginMicrosoftConsent({clientId,redirectUri,sessionId:first.sessionId,
    pendingStore,now:()=>now});
  let exchanged=0;
  await assert.rejects(finishMicrosoftConsent({
    clientId,clientSecret:"fixture-client",redirectUri,
    sessionId:second.sessionId,pendingStore,
    state:new URL(started.authorizationUrl).searchParams.get("state"),
    code:"fixture-authorization-code",now:()=>now,
    credentialStore:{save:async()=>{throw Error("unexpected_write")}},
    fetchImpl:async()=>{exchanged++}
  }),/oauth_state_mismatch/);
  assert.equal(exchanged,0);
  assert.equal(pending.size,0);
});
test("refuses forged JWT with a valid claim body but corrupt signature",async()=>{
  const f=await fixture(),token=await f.sign(f.claims);
  const [header,body,signature]=token.split(".");
  // Mutate the FIRST significant signature character, not trailing Base64URL
  // padding bits that may decode to identical bytes.
  const corrupted=header+"."+body+"."+(signature[0]==="A"?"B":"A")+signature.slice(1);
  await assert.rejects(f.verify(corrupted),/invalid_access_identity/);
});
test("refuses wrong issuer, audience, subject, and expired token",async()=>{
  const f=await fixture();
  for(const claim of [
    {...f.claims,iss:"https://evil.example"},
    {...f.claims,aud:"wrong-audience"},
    {...f.claims,sub:"unknown"},
    {...f.claims,exp:Math.floor(now/1000)-1},
    {...f.claims,type:"org"}
  ])await assert.rejects(f.verify(await f.sign(claim)),/invalid_access_identity/);
});
test("refuses absent header and unsafe team URL",async()=>{
  const f=await fixture();
  await assert.rejects(verifyCloudflareAccessSession(new Request("https://edge.example.com"),
    {teamUrl:issuer,audience,allowedSubjects:["operator-sub-1"]}),/invalid_access_identity/);
  await assert.rejects(f.verify(await f.sign(f.claims),{teamUrl:"https://evil.example"}),/invalid_access_identity/);
});
