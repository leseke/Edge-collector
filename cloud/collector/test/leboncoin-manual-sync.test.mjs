import test from "node:test";
import assert from "node:assert/strict";
import {handleOutlookManualSync} from "../src/leboncoin-manual-sync.mjs";
const origin="https://edge.example.com",path="/internal/outlook/sync";
const key="a".repeat(64);
const env={
  OUTLOOK_ROUTES_ENABLED:"true",OUTLOOK_CONSENT_ENABLED:"true",
  OUTLOOK_INGEST_ENABLED:"true",OUTLOOK_MANUAL_SYNC_ENABLED:"true",
  OUTLOOK_REDIRECT_URI:origin+"/auth/microsoft/callback",
  CF_ACCESS_TEAM_DOMAIN:"https://edge-team.cloudflareaccess.com",
  CF_ACCESS_APP_AUD:"edge-audience-1234",
  CF_ACCESS_ALLOWED_SUBJECTS:"trusted-subject"
};
const request=(options={})=>new Request(origin+(options.path??path),{
  method:options.method??"POST",
  headers:{"Origin":options.origin??origin,"Content-Type":options.contentType??"application/json",
    ...(options.headers??{})},
  ...(options.method==="GET"?{}:{body:options.body??"{}"})
});
function mocks(){
  let verified=0,ran=0;
  return {
    verifySession:async()=>{verified++;return {authenticated:true,ownerKey:key}},
    runCollection:async({ownerKey,maxPages})=>{
      ran++;assert.equal(ownerKey,key);assert.equal(maxPages,3);
      return {status:"OK",complete:true,pages:1,messages_scanned:6,
        matching_alerts:2,inserted_listings:3,already_seen_messages:0}
    },
    get verified(){return verified},get ran(){return ran}
  };
}
test("manual sync remains hidden without all four explicit opt-ins",async()=>{
  for(const flag of ["OUTLOOK_ROUTES_ENABLED","OUTLOOK_CONSENT_ENABLED",
    "OUTLOOK_INGEST_ENABLED","OUTLOOK_MANUAL_SYNC_ENABLED"]){
    const calls=mocks();
    const res=await handleOutlookManualSync({request:request(),env:{...env,[flag]:"false"},...calls});
    assert.equal(res.status,404);assert.equal(calls.verified,0);assert.equal(calls.ran,0);
  }
});
test("method, cross-site origin, content type, request args and hidden owner are denied",async()=>{
  const variants=[
    {method:"GET"},{origin:"https://evil.example"},{contentType:"text/plain"},
    {path:path+"?ownerKey=attacker"},
    {body:'{"maxPages":50}'},{headers:{"X-Owner-Key":"forged"}},
    {headers:{"Authorization":"Bearer bypass"}},
    {headers:{"Sec-Fetch-Site":"cross-site"}}
  ];
  for(const params of variants){
    const calls=mocks();
    const res=await handleOutlookManualSync({request:request(params),env,...calls});
    assert.equal(res.status,404,JSON.stringify(params));assert.equal(calls.ran,0);
    assert.equal(calls.verified,0);
  }
});
test("oversized sync body is rejected before identity validation",async()=>{
  const calls=mocks();
  const res=await handleOutlookManualSync({
    request:request({body:"{}"+"x".repeat(4096)}),env,...calls
  });
  assert.equal(res.status,404);
  assert.equal(calls.verified,0);
  assert.equal(calls.ran,0);
});
test("signed identity, not request input, is passed to bounded collection runner",async()=>{
  const calls=mocks();
  const res=await handleOutlookManualSync({request:request(),env,...calls});
  assert.equal(res.status,200);
  assert.equal(calls.verified,1);assert.equal(calls.ran,1);
  assert.deepEqual(await res.json(),{
    status:"OK",complete:true,pages:1,messages_scanned:6,
    matching_alerts:2,inserted_listings:3,already_seen_messages:0
  });
  assert.equal(res.headers.get("cache-control"),"no-store, private");
});
test("invalid Access assertion fails before any collection",async()=>{
  let invoked=0;
  const res=await handleOutlookManualSync({
    request:request(),env,verifySession:async()=>{throw Error("invalid_access_identity")},
    runCollection:async()=>{invoked++}
  });
  assert.equal(res.status,404);assert.equal(invoked,0);
});
test("no raw mailbox error or secrets leak from failed collection",async()=>{
  const res=await handleOutlookManualSync({
    request:request(),env,verifySession:async()=>({authenticated:true,ownerKey:key}),
    runCollection:async()=>{throw Error("private refresh token and mailbox@example.com")}
  });
  assert.equal(res.status,503);
  assert.deepEqual(await res.json(),{status:"FAILED"});
});
test("concurrent collection is reported as busy, not successful",async()=>{
  const res=await handleOutlookManualSync({
    request:request(),env,verifySession:async()=>({authenticated:true,ownerKey:key}),
    runCollection:async()=>({status:"BUSY",active:false})
  });
  assert.equal(res.status,409);
  assert.deepEqual(await res.json(),{status:"BUSY"});
});
test("unrelated paths do not enter the sync route",async()=>{
  assert.equal(await handleOutlookManualSync({request:request({path:"/other"}),env}),null);
});
