import test from "node:test";
import assert from "node:assert/strict";
import {checkOutlookActivationReadiness} from "../src/leboncoin-activation-check.mjs";
const config={
  OUTLOOK_CLIENT_ID:"123e4567-e89b-12d3-a456-426614174000",
  OUTLOOK_CLIENT_SECRET:"sensitive-test-value",
  OUTLOOK_REDIRECT_URI:"https://edge.example.com/auth/microsoft/callback",
  OUTLOOK_ENCRYPTION_KEY:"ab".repeat(32),
  OUTLOOK_DELTA_ENCRYPTION_KEY:"cd".repeat(32),
  CF_ACCESS_TEAM_DOMAIN:"https://edge-team.cloudflareaccess.com",
  CF_ACCESS_APP_AUD:"edge-application-audience-123456",
  CF_ACCESS_ALLOWED_SUBJECTS:"operator-account-1",
  OUTLOOK_CONSENT_ENABLED:"true",
  DB:{prepare(){},batch(){}}
};
test("reports missing prerequisites without printing any credential",()=>{
  const status=checkOutlookActivationReadiness({});
  assert.equal(status.configured,false);
  assert.equal(status.production_collection_active,false);
  assert.ok(status.missing_or_invalid_bindings.includes("OUTLOOK_CLIENT_ID"));
  assert.equal(JSON.stringify(status).includes("sensitive-test-value"),false);
});
test("configuration readiness is not proof of real OAuth or deployment",()=>{
  const status=checkOutlookActivationReadiness(config);
  assert.equal(status.configured,true);
  assert.equal(status.ready_for_live_consent,true);
  assert.equal(status.microsoft_registration_verified,false);
  assert.equal(status.real_user_consent_verified,false);
  assert.equal(status.production_collection_active,false);
  assert.equal(JSON.stringify(status).includes(config.OUTLOOK_CLIENT_SECRET),false);
  assert.equal(JSON.stringify(status).includes(config.OUTLOOK_ENCRYPTION_KEY),false);
});
test("rejects non-HTTPS callback and multiple operator subjects",()=>{
  const status=checkOutlookActivationReadiness({...config,
    OUTLOOK_REDIRECT_URI:"http://bad.example",CF_ACCESS_ALLOWED_SUBJECTS:"operator1,operator2"});
  assert.ok(status.missing_or_invalid_bindings.includes("OUTLOOK_REDIRECT_URI"));
  assert.ok(status.missing_or_invalid_bindings.includes("CF_ACCESS_ALLOWED_SUBJECTS"));
});
