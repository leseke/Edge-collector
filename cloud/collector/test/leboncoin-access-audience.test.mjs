import test from "node:test";
import assert from "node:assert/strict";
import {resolveCloudflareAccessAudience} from "../src/leboncoin-access-audience.mjs";
import {checkOutlookActivationReadiness} from "../src/leboncoin-activation-check.mjs";

const aud="7c5ed948eea2627d9781cb68865147e7f958baddf000000000000000000";
test("accepts operator's CF_ACCESS_AUD alias without broadening audience",()=>{
  assert.equal(resolveCloudflareAccessAudience({CF_ACCESS_AUD:aud}),aud);
  assert.equal(resolveCloudflareAccessAudience({CF_ACCESS_APP_AUD:aud}),aud);
  assert.equal(resolveCloudflareAccessAudience({
    CF_ACCESS_AUD:aud,CF_ACCESS_APP_AUD:aud
  }),aud);
});
test("fails closed on missing, malformed or conflicting Access audiences",()=>{
  for(const env of [
    {},
    {CF_ACCESS_AUD:"short"},
    {CF_ACCESS_AUD:aud,CF_ACCESS_APP_AUD:"different-audience"},
    {CF_ACCESS_AUD:"abc%def00000"},
    {CF_ACCESS_APP_AUD:aud,CF_ACCESS_AUD:""},
  ])assert.equal(resolveCloudflareAccessAudience(env),null);
});
test("readiness reports canonical binding name when neither valid AUD is available",()=>{
  const env={CF_ACCESS_AUD:"invalid"};
  const res=checkOutlookActivationReadiness(env);
  assert.ok(res.missing_or_invalid_bindings.includes("CF_ACCESS_APP_AUD"));
  assert.equal(res.ready_for_live_consent,false);
});
