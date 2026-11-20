import test from "node:test";
import assert from "node:assert/strict";
import {handleOutlookReadiness} from "../src/leboncoin-readiness-http.mjs";
const origin="https://edge.example.com";
const path="/internal/outlook/readiness";
const env={
  OUTLOOK_ROUTES_ENABLED:"true",
  OUTLOOK_DIAGNOSTICS_ENABLED:"true",
  OUTLOOK_CONSENT_ENABLED:"false",
  OUTLOOK_CLIENT_ID:"123e4567-e89b-12d3-a456-426614174000",
  OUTLOOK_CLIENT_SECRET:"SECRET_VALUE_NEVER_RETURN",
  OUTLOOK_REDIRECT_URI:origin+"/auth/microsoft/callback",
  OUTLOOK_ENCRYPTION_KEY:"ab".repeat(32),
  OUTLOOK_DELTA_ENCRYPTION_KEY:"cd".repeat(32),
  OUTLOOK_ALLOWED_SENDER_DOMAINS:"alerts.example.test",
  CF_ACCESS_TEAM_DOMAIN:"https://edge-team.cloudflareaccess.com",
  CF_ACCESS_APP_AUD:"edge-application-1234",
  CF_ACCESS_ALLOWED_SUBJECTS:"one-approved-operator",
  DB:{prepare(){throw Error("MUST_NOT_QUERY_D1")},batch(){throw Error("MUST_NOT_BATCH_D1")}}
};
const request=(pathValue=path,options={})=>new Request(origin+pathValue,options);
const verified=async()=>({authenticated:true,ownerKey:"a".repeat(64)});
test("diagnostic route falls through for other paths",async()=>{
  assert.equal(await handleOutlookReadiness({
    request:request("/internal/outlook/sync"),env,verifySession:verified
  }),null);
});
test("no route or diagnostic opt-in means no network and private 404",async()=>{
  for(const key of ["OUTLOOK_ROUTES_ENABLED","OUTLOOK_DIAGNOSTICS_ENABLED"]){
    let verifiedCalls=0;
    const res=await handleOutlookReadiness({
      request:request(),env:{...env,[key]:"false"},
      verifySession:async()=>{verifiedCalls++;throw Error("unexpected_auth")}
    });
    assert.equal(res.status,404);
    assert.deepEqual(await res.json(),{error:"not_found"});
    assert.equal(verifiedCalls,0);
  }
});
test("unsafe method, origin, query and supplied credentials fail before Access verification",async()=>{
  for(const req of [
    request(path,{method:"POST",body:"{}"}),
    request(path+"?debug=1"),
    request(path,{headers:{Authorization:"Bearer override"}}),
    request(path,{headers:{"X-Owner-Key":"fake"}}),
    new Request("https://other.example.com"+path)
  ]){
    let verifiedCalls=0;
    const res=await handleOutlookReadiness({
      request:req,env,verifySession:async()=>{verifiedCalls++;throw Error("unexpected_auth")}
    });
    assert.equal(res.status,404);assert.equal(verifiedCalls,0);
  }
});
test("unsigned or invalid identity cannot inspect binding names",async()=>{
  const res=await handleOutlookReadiness({
    request:request(),env,verifySession:async()=>{throw Error("invalid_access_identity")}
  });
  assert.equal(res.status,404);
  assert.deepEqual(await res.json(),{error:"not_found"});
});
test("authenticated operator sees only binding status, no secrets or false verified claims",async()=>{
  let verifiedCalls=0;
  const res=await handleOutlookReadiness({
    request:request(),env,
    verifySession:async(_request,opts)=>{
      verifiedCalls++;
      assert.deepEqual(opts.allowedSubjects,["one-approved-operator"]);
      assert.equal(opts.audience,env.CF_ACCESS_APP_AUD);
      return verified();
    }
  });
  assert.equal(res.status,200);
  assert.equal(verifiedCalls,1);
  const body=await res.json();
  assert.equal(body.status,"CONFIGURATION_ONLY_NOT_LIVE_VERIFIED");
  assert.equal(body.configured,true);
  assert.equal(body.ready_for_live_consent,false);
  assert.equal(body.switches.routes,true);
  assert.equal(body.switches.consent,false);
  assert.equal(body.external_verification.remote_d1_migrations,"NOT_VERIFIED");
  assert.equal(body.external_verification.microsoft_registration,"NOT_VERIFIED");
  assert.deepEqual(body.missing_or_invalid_bindings,[]);
  const serialized=JSON.stringify(body);
  for(const secret of [env.OUTLOOK_CLIENT_SECRET,env.OUTLOOK_ENCRYPTION_KEY,
    env.OUTLOOK_DELTA_ENCRYPTION_KEY,env.CF_ACCESS_ALLOWED_SUBJECTS,
    env.OUTLOOK_ALLOWED_SENDER_DOMAINS]){
    assert.equal(serialized.includes(secret),false);
  }
  assert.equal(res.headers.get("cache-control"),"no-store, private");
});
test("missing bindings are reported only to verified operator without reading D1",async()=>{
  const res=await handleOutlookReadiness({
    request:request(),env:{...env,OUTLOOK_CLIENT_SECRET:undefined},
    verifySession:verified
  });
  assert.equal(res.status,200);
  const body=await res.json();
  assert.equal(body.configured,false);
  assert.ok(body.missing_or_invalid_bindings.includes("OUTLOOK_CLIENT_SECRET"));
  assert.equal(body.external_verification.independent_user_consent,"NOT_VERIFIED");
});
