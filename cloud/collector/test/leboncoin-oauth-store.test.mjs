import test from "node:test";
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {createD1OAuthStores} from "../src/leboncoin-oauth-store.mjs";
import {beginMicrosoftConsent,finishMicrosoftConsent} from "../src/leboncoin-consent.mjs";
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const encryptionKey="ab".repeat(32),mailboxKey="1".repeat(32);
const clientId="123e4567-e89b-12d3-a456-426614174000";
const redirectUri="https://edge.example.com/auth/microsoft/callback";
const sessionId="session_bound_to_login_123456789";
function dbFixture(){
  const pending=new Map(),credentials=new Map();
  return {pending,credentials,
    prepare(sql) {return {bind(...params) {return {
      async run(){
        if(sql.includes("INSERT INTO lbc_oauth_pending")){
          if(pending.has(params[0]))throw Error("duplicate_state");
          pending.set(params[0],{nonce_b64:params[1],ciphertext_b64:params[2],expires_at:params[3]});
          return {meta:{changes:1}};
        }
        if(sql.includes("INSERT OR IGNORE INTO lbc_oauth_credentials")){
          if(credentials.has(params[0]))return {meta:{changes:0}};
          credentials.set(params[0],{nonce_b64:params[1],ciphertext_b64:params[2],generation:1});
          return {meta:{changes:1}};
        }
        if(sql.includes("UPDATE lbc_oauth_credentials")){
          const row=credentials.get(params[3]);
          if(!row || row.generation!==params[4])return {meta:{changes:0}};
          credentials.set(params[3],{nonce_b64:params[0],ciphertext_b64:params[1],generation:row.generation+1});
          return {meta:{changes:1}};
        }
        throw Error("unknown SQL");
      },
      async first(){
        if(sql.includes("DELETE FROM lbc_oauth_pending")){
          const row=pending.get(params[0])||null;
          pending.delete(params[0]);return row;
        }
        if(sql.includes("SELECT nonce_b64,ciphertext_b64,generation")){
          return credentials.get(params[0])||null;
        }
        throw Error("unknown query");
      }
    }}}}
  };
}
test("PKCE state is encrypted at rest and consumed atomically",async()=>{
  const db=dbFixture();
  const a=await createD1OAuthStores({db,mailboxKey,encryptionKey});
  const start=await beginMicrosoftConsent({
    clientId,redirectUri,sessionId,pendingStore:a.pendingStore});
  const state=new URL(start.authorizationUrl).searchParams.get("state");
  assert.equal(db.pending.size,1);
  assert.equal(JSON.stringify([...db.pending.values()]).includes("verifier"),false);
  const result=await finishMicrosoftConsent({
    clientId,redirectUri,sessionId,state,code:"authorization-code-1234",
    clientSecret:"secret",pendingStore:a.pendingStore,credentialStore:a.credentialStore,
    fetchImpl:async()=>({ok:true,json:async()=>({access_token:"short-lived",
      refresh_token:"long-lived-private",expires_in:3600})})
  });
  assert.equal(result.connected,true);
  assert.equal(db.pending.size,0);
  assert.equal(db.credentials.size,1);
  assert.equal(JSON.stringify([...db.credentials.values()]).includes("long-lived-private"),false);
  const restored=await createD1OAuthStores({db,mailboxKey,encryptionKey});
  assert.deepEqual(await restored.credentialStore.load(),{refreshToken:"long-lived-private"});
  await assert.rejects(a.pendingStore.consume("nope"),/invalid_oauth_state_hash/);
});
test("encrypted refresh-token updates reject stale concurrent writes",async()=>{
  const db=dbFixture();
  const a=await createD1OAuthStores({db,mailboxKey,encryptionKey});
  const b=await createD1OAuthStores({db,mailboxKey,encryptionKey});
  await a.credentialStore.load();await b.credentialStore.load();
  await a.credentialStore.save({refreshToken:"first"});
  await assert.rejects(b.credentialStore.save({refreshToken:"stale"}),/oauth_credential_concurrent_update/);
  assert.equal((await a.credentialStore.load()).refreshToken,"first");
});
test("wrong envelope key refuses to decrypt private credentials",async()=>{
  const db=dbFixture();
  const a=await createD1OAuthStores({db,mailboxKey,encryptionKey});
  await a.credentialStore.save({refreshToken:"private"});
  const b=await createD1OAuthStores({db,mailboxKey,encryptionKey:"cd".repeat(32)});
  await assert.rejects(b.credentialStore.load(),/oauth_secret_decryption_failed/);
});
