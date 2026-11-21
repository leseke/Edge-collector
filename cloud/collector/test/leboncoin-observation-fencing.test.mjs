import test from "node:test";
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {persistLeboncoinAlerts} from "../src/leboncoin-d1.mjs";
import {parseLeboncoinAlert} from "../src/leboncoin-email.mjs";
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const lease={ownerKey:"a".repeat(64),leaseId:"123e4567-e89b-12d3-a456-426614174000"};
const sample=()=>parseLeboncoinAlert({id:"fixture-mail",
  subject:"Pokémon ME6 : 38 nouveaux résultats",
  receivedDateTime:"2026-11-19T05:21:31Z",
  body:{content:'| [ETB Pokémon 75 € Evreux](https://www.leboncoin.fr/vi/3312468604.htm)'}});
function fakeDb(active=true){
  const calls=[];return {calls,prepare(sql){return {bind(...params){
    if(sql.startsWith("SELECT 1 AS seen"))return {first:async()=>null};
    return {sql,params};
  }}},async batch(stmts){
    calls.push(stmts);
    for(const s of stmts.slice(0,-1)){
      assert.match(s.sql,/EXISTS \(SELECT 1 FROM lbc_sync_lease/);
      assert.deepEqual(s.params.slice(-3,-1),[lease.ownerKey,lease.leaseId]);
      assert.equal(Number.isSafeInteger(s.params.at(-1)),true);
    }
    return stmts.map((_,i)=>({meta:{changes:i===stmts.length-1?0:(active?1:0)}}));
  }};
}
test("append-only alerts and listings are fenced within each D1 INSERT",async()=>{
  const db=fakeDb(true);
  const r=await persistLeboncoinAlerts(db,[sample()],{lease});
  assert.equal(r.inserted_messages,1);
  assert.equal(r.inserted_listings,1);
  assert.equal(db.calls.length,1);
});
test("a replaced lease prevents message insert and is not reported as a duplicate",async()=>{
  const db=fakeDb(false);
  await assert.rejects(persistLeboncoinAlerts(db,[sample()],{lease}),
    /outlook_observation_lease_lost_or_conflict/);
});
test("rejects foreign owner or malformed lease ID before any writes",async()=>{
  const db=fakeDb();
  await assert.rejects(persistLeboncoinAlerts(db,[sample()],{
    lease:{ownerKey:"x",leaseId:lease.leaseId}}),/invalid_lbc_lease/);
  assert.equal(db.calls.length,0);
});
