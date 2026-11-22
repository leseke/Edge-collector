import test from "node:test";
import assert from "node:assert/strict";
import {handleOutlookWorkerRoute} from "../src/leboncoin-worker-http.mjs";
const request=(path,method="GET")=>new Request("https://edge.example.com"+path,{method});
const guarded="/auth/microsoft/start";
const callback="/auth/microsoft/callback?code=fixture&state=fixture";
test("unrelated Worker routes fall through unchanged",async()=>{
  const result=await handleOutlookWorkerRoute({
    request:request("/internal/collect"),env:{},fetchImpl:async()=>{throw Error("network")}
  });
  assert.equal(result,null);
});
test("both consent flags must be enabled before any OAuth or D1 access",async()=>{
  let queries=0,network=0;
  const db={prepare(){queries++;throw Error("unexpected_db")}};
  const fetchImpl=async()=>{network++;throw Error("unexpected_network")};
  for(const env of [
    {DB:db},
    {DB:db,OUTLOOK_ROUTES_ENABLED:"true"},
    {DB:db,OUTLOOK_CONSENT_ENABLED:"true"},
    {DB:db,OUTLOOK_ROUTES_ENABLED:"TRUE",OUTLOOK_CONSENT_ENABLED:"true"}
  ]){
    for(const uri of [guarded,callback]){
      const res=await handleOutlookWorkerRoute({request:request(uri),env,fetchImpl});
      assert.equal(res.status,404);
      assert.equal(res.headers.get("cache-control"),"no-store, private");
      assert.deepEqual(await res.json(),{error:"not_found"});
    }
  }
  assert.equal(queries,0);assert.equal(network,0);
});
test("enabling flags without independently provisioned secrets fails closed",async()=>{
  let calls=0;
  const env={OUTLOOK_ROUTES_ENABLED:"true",OUTLOOK_CONSENT_ENABLED:"true",
    DB:{prepare(){calls++;throw Error("db")}}};
  const res=await handleOutlookWorkerRoute({request:request(guarded),env,
    fetchImpl:async()=>{calls++;throw Error("network")}});
  assert.equal(res.status,404);
  assert.deepEqual(await res.json(),{error:"not_found"});
  assert.equal(calls,0);
});
test("configured but unsigned Cloudflare Access request is refused before D1 writes",async()=>{
  let queried=0,network=0;
  const env={
    OUTLOOK_ROUTES_ENABLED:"true",OUTLOOK_CONSENT_ENABLED:"true",
    OUTLOOK_CLIENT_ID:"123e4567-e89b-12d3-a456-426614174000",
    OUTLOOK_CLIENT_SECRET:"fixture-not-real",
    OUTLOOK_REDIRECT_URI:"https://edge.example.com/auth/microsoft/callback",
    OUTLOOK_ENCRYPTION_KEY:"ab".repeat(32),
    CF_ACCESS_TEAM_DOMAIN:"https://edge-team.cloudflareaccess.com",
    CF_ACCESS_APP_AUD:"edge-audience-1234",
    CF_ACCESS_ALLOWED_SUBJECTS:"operator-sub-1",
    DB:{prepare(){queried++;throw Error("unexpected_db")}}
  };
  const res=await handleOutlookWorkerRoute({request:request(guarded),env,
    fetchImpl:async()=>{network++;throw Error("unexpected_network")}});
  assert.equal(res.status,404);
  assert.equal(queried,0);assert.equal(network,0);
});
