import test from "node:test";
import assert from "node:assert/strict";
import {createAccessProtectedOutlookConsent} from "../src/leboncoin-access-consent.mjs";
const config={
  DB:{prepare(){throw Error("should_not_query_db")}},
  OUTLOOK_ENCRYPTION_KEY:"ab".repeat(32),
  CF_ACCESS_TEAM_DOMAIN:"https://edge-team.cloudflareaccess.com",
  CF_ACCESS_APP_AUD:"edge-audience-1234",
  CF_ACCESS_ALLOWED_SUBJECTS:"operator-sub-1",
  OUTLOOK_CLIENT_ID:"123e4567-e89b-12d3-a456-426614174000",
  OUTLOOK_CLIENT_SECRET:"nonproduction-fixture",
  OUTLOOK_REDIRECT_URI:"https://edge-outlook-collector.ylan-seke.workers.dev/auth/microsoft/callback",
  OUTLOOK_CONSENT_ENABLED:"false"
};
test("requires operator allowlist and all server-only environment bindings",()=>{
  assert.throws(()=>createAccessProtectedOutlookConsent({env:{...config,OUTLOOK_ENCRYPTION_KEY:null}}),/missing_outlook_consent_config/);
  assert.throws(()=>createAccessProtectedOutlookConsent({env:{...config,CF_ACCESS_ALLOWED_SUBJECTS:"a,b"}}),/operator_allowlist_required/);
});
test("rejects callbacks pointing to TCG, a foreign host, and alternate paths",()=>{
  for(const redirect of [
    "https://edge-tcg-collector.ylan-seke.workers.dev/auth/microsoft/callback",
    "https://edge-outlook-collector.ylan-seke.workers.dev/auth/microsoft/callback/",
    "https://example.com/auth/microsoft/callback",
    "http://edge-outlook-collector.ylan-seke.workers.dev/auth/microsoft/callback"
  ]){
    assert.throws(()=>createAccessProtectedOutlookConsent({
      env:{...config,OUTLOOK_REDIRECT_URI:redirect}
    }),/invalid_outlook_redirect_uri/,redirect);
  }
});
test("disabled by default makes no Access network calls or D1 writes",async()=>{
  let calls=0;
  const handler=createAccessProtectedOutlookConsent({env:config,fetchImpl:async()=>{
    calls++;throw Error("no_network_allowed");
  }});
  const res=await handler(new Request("https://edge.example.com/auth/microsoft/start"));
  assert.equal(res.status,404);
  assert.equal(calls,0);
  assert.equal(res.headers.get("cache-control"),"no-store, private");
});
