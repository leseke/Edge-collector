import test from "node:test";
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {createEncryptedD1DeltaStore} from "../src/leboncoin-delta-store.mjs";
if (!globalThis.crypto) globalThis.crypto=webcrypto;
const ownerKey="a".repeat(64),encryptionKey="cd".repeat(32);
const leaseId="123e4567-e89b-12d3-a456-426614174000";
function fixture(active=true){
  let cursor=null,leaseActive=active;
  return {
    setLease(value){leaseActive=value},
    get cursor(){return cursor},
    prepare(sql){return {bind(...args){return {
      first:async()=>cursor,
      run:async()=>{
        assert.match(sql,/EXISTS \(SELECT 1 FROM lbc_sync_lease/);
        const idArg=args.at(-2), ownerArg=args.at(-3),epoch=args.at(-1);
        assert.equal(ownerArg,ownerKey);
        assert.equal(idArg,leaseId);
        assert.equal(Number.isSafeInteger(epoch),true);
        if (!leaseActive)return {meta:{changes:0}};
        if(sql.startsWith("INSERT")){
          if(cursor)return {meta:{changes:0}};
          cursor={nonce_b64:args[1],ciphertext_b64:args[2],generation:1};
        }else{
          if(!cursor||cursor.generation!==args[4])return {meta:{changes:0}};
          cursor={nonce_b64:args[0],ciphertext_b64:args[1],generation:cursor.generation+1};
        }
        return {meta:{changes:1}};
      }
    }}}}
  };
}
test("fenced cursor refuses first insert after losing D1 lease",async()=>{
  const db=fixture(false);
  const store=await createEncryptedD1DeltaStore({db,mailboxKey:ownerKey,encryptionKey,
    lease:{ownerKey,leaseId}});
  await store.load();
  await assert.rejects(store.save("cursor-A"),/delta_cursor_lease_lost_or_conflict/);
  assert.equal(db.cursor,null);
});
test("fenced cursor rejects replacement lease before update",async()=>{
  const db=fixture(true);
  const store=await createEncryptedD1DeltaStore({db,mailboxKey:ownerKey,encryptionKey,
    lease:{ownerKey,leaseId}});
  await store.load();
  await store.save("cursor-A");
  assert.equal(db.cursor.generation,1);
  db.setLease(false);
  await assert.rejects(store.save("cursor-B"),/delta_cursor_lease_lost_or_conflict/);
  assert.equal(db.cursor.generation,1);
});
test("cannot use another mailbox owner's lease",async()=>{
  await assert.rejects(createEncryptedD1DeltaStore({db:fixture(),mailboxKey:ownerKey,
    encryptionKey,lease:{ownerKey:"b".repeat(64),leaseId}}),/invalid_delta_lease/);
});
