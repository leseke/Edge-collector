import test from "node:test";
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {withOutlookRunLease} from "../src/leboncoin-run-lease.mjs";
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const ownerKey="a".repeat(64);
function fakeDb(){
  const locks=new Map();let now=10000;
  return {locks,now:()=>now,setNow:v=>{now=v},
    prepare(sql){return {bind(...args){return {
      async run(){
        if(sql.startsWith("INSERT INTO lbc_sync_lease")){
          const [owner,id,expiry,acquired]=args;
          const prev=locks.get(owner);
          if(prev && prev.expiry>acquired)return {meta:{changes:0}};
          locks.set(owner,{id,expiry});
          return {meta:{changes:1}};
        }
        if(sql.startsWith("DELETE FROM lbc_sync_lease")){
          const [owner,id]=args;
          if(locks.get(owner)?.id===id){locks.delete(owner);return {meta:{changes:1}}}
          return {meta:{changes:0}};
        }
        throw Error("unexpected SQL");
      }
    }}}}
  };
}
test("locks per-owner, reports BUSY and releases on success",async()=>{
  const db=fakeDb();
  let resume;
  const gate=new Promise(resolve=>resume=resolve);
  const first=withOutlookRunLease({db,ownerKey,clock:db.now,run:async()=>{await gate;return {status:"OK"}}});
  // let first lock be acquired before the second attempt
  await new Promise(resolve=>setImmediate(resolve));
  const busy=await withOutlookRunLease({db,ownerKey,clock:db.now,run:async()=>{throw Error("overlap")}});
  assert.deepEqual(busy,{status:"BUSY",active:false});
  resume();
  assert.deepEqual(await first,{status:"OK"});
  assert.equal(db.locks.size,0);
});
test("releases lock after failure, and does not delete replaced lease",async()=>{
  const db=fakeDb();
  await assert.rejects(withOutlookRunLease({db,ownerKey,clock:db.now,run:async()=>{throw Error("failed")}}),/failed/);
  assert.equal(db.locks.size,0);
  await assert.rejects(withOutlookRunLease({db,ownerKey,clock:db.now,leaseMs:1000,run:async()=>{
    db.setNow(12000);
    // replaced lock cannot be deleted by old owner when run finishes.
    db.locks.set(ownerKey,{id:"replacement",expiry:14000});
  }}),/outlook_run_lease_expired/);
  assert.equal(db.locks.get(ownerKey).id,"replacement");
});
test("disabled inputs and untrusted owner keys cannot claim lock",async()=>{
  await assert.rejects(withOutlookRunLease({db:fakeDb(),ownerKey:"not-owner",run:async()=>{}}),/invalid_outlook_lease_config/);
});
