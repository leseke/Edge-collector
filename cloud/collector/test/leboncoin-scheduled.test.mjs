import test from "node:test";
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {runScheduledOutlookCollection} from "../src/leboncoin-scheduled.mjs";
import {deriveCloudflareAccessOwnerKey} from "../src/leboncoin-access-session.mjs";
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const env={
  OUTLOOK_INGEST_ENABLED:"true",
  OUTLOOK_SCHEDULE_ENABLED:"true",
  CF_ACCESS_TEAM_DOMAIN:"https://edge-team.cloudflareaccess.com",
  CF_ACCESS_APP_AUD:"edge-audience-1234",
  CF_ACCESS_ALLOWED_SUBJECTS:"trusted-subject"
};
test("scheduler is inert unless both independent flags are true",async()=>{
  let invoked=0;
  for(const flags of [{},{OUTLOOK_INGEST_ENABLED:"true"},
    {OUTLOOK_SCHEDULE_ENABLED:"true"},
    {OUTLOOK_INGEST_ENABLED:"TRUE",OUTLOOK_SCHEDULE_ENABLED:"true"}]){
    const result=await runScheduledOutlookCollection({
      env:flags,scheduledTime:123456789,
      runCollection:async()=>{invoked++;throw Error("unexpected")}
    });
    assert.deepEqual(result,{status:"DISABLED",active:false});
  }
  assert.equal(invoked,0);
});
test("scheduled owner matches exact Cloudflare Access identity derivation",async()=>{
  const expected=await deriveCloudflareAccessOwnerKey({
    teamUrl:env.CF_ACCESS_TEAM_DOMAIN,audience:env.CF_ACCESS_APP_AUD,
    subject:"trusted-subject"
  });
  let calls=0;
  const result=await runScheduledOutlookCollection({env,scheduledTime:123456789,
    runCollection:async args=>{
      calls++;
      assert.equal(args.env,env);
      assert.equal(args.ownerKey,expected);
      assert.match(args.ownerKey,/^[a-f0-9]{64}$/);
      assert.equal(args.maxPages,3);
      return {status:"OK",active:true,complete:true,
        refreshToken:"private",messageBody:"never returned"};
    }});
  assert.deepEqual(result,{status:"OK",active:true,complete:true});
  assert.equal(calls,1);
  assert.equal(JSON.stringify(result).includes("private"),false);
});
test("scheduler refuses missing operator, ambiguous owner and unsafe issuer",async()=>{
  let calls=0;
  for(const e of [
    {...env,CF_ACCESS_ALLOWED_SUBJECTS:""},
    {...env,CF_ACCESS_ALLOWED_SUBJECTS:"first,second"},
    {...env,CF_ACCESS_TEAM_DOMAIN:"https://evil.example"},
    {...env,CF_ACCESS_APP_AUD:"bad"}
  ]){
    await assert.rejects(runScheduledOutlookCollection({
      env:e,scheduledTime:123456789,runCollection:async()=>{calls++}
    }),/outlook_schedule_not_configured|invalid_access_identity/);
  }
  assert.equal(calls,0);
});
test("scheduler rejects forged event time and unknown result status",async()=>{
  await assert.rejects(runScheduledOutlookCollection({
    env,scheduledTime:"2026-11-20",runCollection:async()=>{}
  }),/outlook_schedule_not_configured/);
  await assert.rejects(runScheduledOutlookCollection({
    env,scheduledTime:123456789,runCollection:async()=>({status:"UNTRUSTED"})
  }),/outlook_schedule_unexpected_status/);
});
test("overlapping scheduled run returns BUSY without exposing private details",async()=>{
  const result=await runScheduledOutlookCollection({
    env,scheduledTime:123456789,
    runCollection:async()=>({status:"BUSY",active:false,ownerKey:"private"})
  });
  assert.deepEqual(result,{status:"BUSY",active:false,complete:false});
});
