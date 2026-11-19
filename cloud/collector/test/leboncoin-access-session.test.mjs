import test from "node:test";
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {verifyCloudflareAccessSession} from "../src/leboncoin-access-session.mjs";
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
test("refuses forged JWT with a valid claim body but corrupt signature",async()=>{
  const f=await fixture(),token=await f.sign(f.claims);
  const corrupted=token.slice(0,-1)+(token.endsWith("A")?"B":"A");
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
