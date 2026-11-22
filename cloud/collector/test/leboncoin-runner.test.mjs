import {webcrypto} from "node:crypto";
if (!globalThis.crypto) globalThis.crypto=webcrypto;
import test from "node:test";
import assert from "node:assert/strict";
import {runOutlookLeboncoinCollection} from "../src/leboncoin-runner.mjs";
test("disabled collector never touches D1, OAuth or network",async()=>{
  let touched=0;
  const result=await runOutlookLeboncoinCollection({
    env:{OUTLOOK_INGEST_ENABLED:"false",DB:{prepare(){touched++;throw Error("db")}}},
    ownerKey:"a".repeat(64),
    fetchImpl:async()=>{touched++;throw Error("network")}
  });
  assert.deepEqual(result,{status:"DISABLED",active:false});
  assert.equal(touched,0);
});
test("enabled collector refuses missing or unverified configuration",async()=>{
  await assert.rejects(runOutlookLeboncoinCollection({
    env:{OUTLOOK_INGEST_ENABLED:"true"},ownerKey:"spoofed"
  }),/outlook_runtime_not_configured/);
});
test("no independent Microsoft OAuth consent means no token request",async()=>{
  let networkCalls=0;
  const env={
    OUTLOOK_INGEST_ENABLED:"true",
    OUTLOOK_ENCRYPTION_KEY:"ab".repeat(32),
    OUTLOOK_DELTA_ENCRYPTION_KEY:"cd".repeat(32),
    OUTLOOK_CLIENT_ID:"123e4567-e89b-12d3-a456-426614174000",
    OUTLOOK_CLIENT_SECRET:"private",
    DB:{prepare(sql){
      if(sql.startsWith("INSERT INTO lbc_sync_lease"))return {bind(){return {run:async()=>({meta:{changes:1}})}}};
      if(sql.startsWith("DELETE FROM lbc_sync_lease"))return {bind(){return {run:async()=>({meta:{changes:1}})}}};
      if(sql.startsWith("SELECT lease_id,expires_at_ms FROM lbc_sync_lease"))return {bind(){return {first:async()=>({lease_id:"unused",expires_at_ms:Date.now()+120000})}}};
      assert.match(sql,/lbc_oauth_credentials/);
      return {bind(){return {first:async()=>null}}}
    },batch(){}}
  };
  await assert.rejects(runOutlookLeboncoinCollection({
    env,ownerKey:"a".repeat(64),fetchImpl:async()=>{networkCalls++;throw Error("unexpected")}
  }),/outlook_requires_verified_consent/);
  assert.equal(networkCalls,0);
});
