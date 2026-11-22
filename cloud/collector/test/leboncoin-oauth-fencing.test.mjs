import test from "node:test";
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {createD1OAuthStores} from "../src/leboncoin-oauth-store.mjs";
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const ownerKey="a".repeat(64),leaseId="123e4567-e89b-12d3-a456-426614174000";
const encryptionKey="ab".repeat(32);
function fakeDb(validLease){
  let row=null;const writes=[];
  return {writes,prepare(sql){return {bind(...params){return {
    first:async()=>row,
    run:async()=>{
      writes.push({sql,params});
      assert.match(sql,/EXISTS \(SELECT 1 FROM lbc_sync_lease/);
      assert.deepEqual(params.slice(-3,-1),[ownerKey,leaseId]);
      assert.equal(Number.isSafeInteger(params.at(-1)),true);
      if(!validLease)return {meta:{changes:0}};
      if(sql.includes("INSERT OR IGNORE INTO lbc_oauth_credentials")){
        if(row)return {meta:{changes:0}};
        row={nonce_b64:params[1],ciphertext_b64:params[2],generation:1};
      }else if(sql.includes("UPDATE lbc_oauth_credentials")){
        if(!row || row.generation!==params[4])return {meta:{changes:0}};
        row={nonce_b64:params[0],ciphertext_b64:params[1],generation:2};
      }
      return {meta:{changes:1}};
    }
  }}}}};
}
test("initial OAuth credential insert is fenced by current owner lease",async()=>{
  const db=fakeDb(true);
  const stores=await createD1OAuthStores({db,mailboxKey:ownerKey,encryptionKey,
    lease:{ownerKey,leaseId}});
  await stores.credentialStore.save({refreshToken:"first",accountId:"GraphUser1"});
  await stores.credentialStore.save({refreshToken:"rotated"});
  assert.equal(db.writes.length,2);
});
test("lost lease prevents token rotation or first-time insertion",async()=>{
  const db=fakeDb(false);
  const stores=await createD1OAuthStores({db,mailboxKey:ownerKey,encryptionKey,
    lease:{ownerKey,leaseId}});
  await assert.rejects(stores.credentialStore.save({refreshToken:"first"}),
    /oauth_credential_lease_lost_or_conflict/);
});
test("foreign account lease cannot be used",async()=>{
  await assert.rejects(createD1OAuthStores({db:fakeDb(true),mailboxKey:ownerKey,
    encryptionKey,lease:{ownerKey:"b".repeat(64),leaseId}}),/invalid_oauth_lease/);
});
