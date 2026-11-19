import test from "node:test";
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {beginMicrosoftConsent,finishMicrosoftConsent} from "../src/leboncoin-consent.mjs";
if (!globalThis.crypto) globalThis.crypto=webcrypto;
const clientId="123e4567-e89b-12d3-a456-426614174000";
const redirectUri="https://edge.example.com/auth/microsoft/callback";
const sessionId="session_bound_to_login_123456789";
function fixture() {
  const pending=new Map(), saved=[];
  return {saved,pendingStore:{
    async create(v){if(pending.has(v.stateHash))throw Error("collision");pending.set(v.stateHash,v)},
    async consume(hash){const item=pending.get(hash);pending.delete(hash);return item||null}
  },credentialStore:{async save(x){saved.push(x)}}};
}
const options = x => ({clientId,redirectUri,sessionId,...x});
test("Microsoft authorize URL uses PKCE S256, narrow scopes and state",async()=>{
  const f=fixture();
  const started=await beginMicrosoftConsent(options(f));
  const u=new URL(started.authorizationUrl);
  assert.equal(u.origin,"https://login.microsoftonline.com");
  assert.equal(u.searchParams.get("response_type"),"code");
  assert.equal(u.searchParams.get("scope"),"offline_access Mail.Read");
  assert.equal(u.searchParams.get("code_challenge_method"),"S256");
  assert.ok(u.searchParams.get("code_challenge").length>=43);
  assert.ok(u.searchParams.get("state").length>=40);
  assert.equal(u.searchParams.has("code_verifier"),false);
});
test("single-use matching callback exchanges code, stores refresh token, not access token",async()=>{
  const f=fixture();
  const started=await beginMicrosoftConsent(options(f));
  const state=new URL(started.authorizationUrl).searchParams.get("state");
  let called=0;
  const exchange=async (_url,req)=>{
    called++;
    const p=new URLSearchParams(req.body);
    assert.equal(p.get("grant_type"),"authorization_code");
    assert.equal(p.get("scope"),"offline_access Mail.Read");
    assert.equal(p.get("redirect_uri"),redirectUri);
    assert.ok(p.get("code_verifier").length>=43);
    assert.equal(p.get("code"),"authorization-code-1234");
    return {ok:true,json:async()=>({access_token:"access",refresh_token:"refresh",
      expires_in:3600})};
  };
  const args=options({...f,state,code:"authorization-code-1234",clientSecret:"private-secret",fetchImpl:exchange});
  const finished=await finishMicrosoftConsent(args);
  assert.equal(finished.connected,true);
  assert.deepEqual(f.saved,[{refreshToken:"refresh"}]);
  await assert.rejects(finishMicrosoftConsent(args),/oauth_state_expired_or_replayed/);
  assert.equal(called,1);
});
test("callback fails closed on session substitution",async()=>{
  const f=fixture(),start=await beginMicrosoftConsent(options(f));
  const state=new URL(start.authorizationUrl).searchParams.get("state");
  await assert.rejects(finishMicrosoftConsent(options({...f,sessionId:"other_session_123456789",state,
    code:"authorization-code-1234",clientSecret:"private-secret",
    fetchImpl:async()=>{throw Error("must not exchange")}})),/oauth_state_mismatch/);
  assert.equal(f.saved.length,0);
});
test("state expiration prevents token exchange",async()=>{
  const f=fixture(),start=await beginMicrosoftConsent(options({...f,now:()=>1000}));
  const state=new URL(start.authorizationUrl).searchParams.get("state");
  await assert.rejects(finishMicrosoftConsent(options({...f,state,
    code:"authorization-code-1234",clientSecret:"private-secret",now:()=>900000,
    fetchImpl:async()=>{throw Error("must not exchange")}})),/oauth_state_mismatch/);
});
test("rejects insecure redirect URI and absent authenticated session",async()=>{
  const f=fixture();
  await assert.rejects(beginMicrosoftConsent(options({...f,redirectUri:"http://evil.example/callback"})),/invalid_microsoft_redirect_uri/);
  await assert.rejects(beginMicrosoftConsent(options({...f,sessionId:"no"})),/invalid_oauth_session/);
});
test("credential storage failure cannot be reported as successful connection",async()=>{
  const f=fixture(),start=await beginMicrosoftConsent(options(f));
  const state=new URL(start.authorizationUrl).searchParams.get("state");
  await assert.rejects(finishMicrosoftConsent(options({...f,state,
    code:"authorization-code-1234",clientSecret:"private-secret",
    credentialStore:{save:async()=>{throw Error("store_down")}},
    fetchImpl:async()=>({ok:true,json:async()=>({
      access_token:"access",refresh_token:"refresh",expires_in:3600})})})),/store_down/);
});
