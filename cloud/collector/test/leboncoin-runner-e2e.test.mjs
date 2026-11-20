import test from "node:test";
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {createD1OAuthStores} from "../src/leboncoin-oauth-store.mjs";
import {runOutlookLeboncoinCollection} from "../src/leboncoin-runner.mjs";
if(!globalThis.crypto)globalThis.crypto=webcrypto;

const OWNER="a".repeat(64),OAUTH_KEY="ab".repeat(32),DELTA_KEY="cd".repeat(32);
const CLIENT="123e4567-e89b-12d3-a456-426614174000";
const CURSOR="https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages/delta?$deltatoken=test";
const MAIL={id:"email-001",subject:"Pokémon 30 ans : 3 nouveaux résultats",
  receivedDateTime:"2026-11-20T07:00:00Z",
  from:{emailAddress:{address:"alerts@notifications.example.test"}},
  sender:{emailAddress:{address:"alerts@notifications.example.test"}},
  body:{contentType:"html",content:'<a href="https://www.leboncoin.fr/vi/3312500756.htm">Dracaufeu 160 € Paris</a>'}};

// A D1 contract fixture that persists encrypted ciphertext across entirely
// separate runner invocations. No OAuth or Graph endpoint is contacted.
function makeD1(){
  const state={lock:null,credentials:null,cursor:null,messages:new Map(),listings:new Map()};
  const db={
    state,
    prepare(sql){return {bind(...params){return {
      sql,params,
      async first(){
        if(sql.startsWith("SELECT lease_id,expires_at_ms FROM lbc_sync_lease"))
          return state.lock ? {lease_id:state.lock.id,expires_at_ms:state.lock.expiry}:null;
        if(sql.includes("FROM lbc_oauth_credentials"))return state.credentials;
        if(sql.includes("FROM lbc_graph_delta_cursor"))return state.cursor;
        if(sql.startsWith("SELECT 1 AS seen FROM lbc_alert_messages"))
          return state.messages.has(params[0]) ? {seen:1}:null;
        throw Error("unexpected_d1_first:"+sql);
      },
      async run(){
        if(sql.startsWith("INSERT INTO lbc_sync_lease")){
          const [owner,id,expiry,now]=params;
          if(state.lock && state.lock.expiry>now)return {meta:{changes:0}};
          state.lock={owner,id,expiry};return {meta:{changes:1}};
        }
        if(sql.startsWith("DELETE FROM lbc_sync_lease")){
          if(state.lock?.owner===params[0] && state.lock.id===params[1]){
            state.lock=null;return {meta:{changes:1}};
          }return {meta:{changes:0}};
        }
        const fenced=sql.includes("lbc_sync_lease WHERE owner_key");
        if(fenced){
          const [owner,id,when]=params.slice(-3);
          if(!state.lock || state.lock.owner!==owner || state.lock.id!==id ||
             state.lock.expiry<=when)return {meta:{changes:0}};
        }
        if(sql.includes("INSERT OR IGNORE INTO lbc_oauth_credentials")){
          if(state.credentials)return {meta:{changes:0}};
          state.credentials={nonce_b64:params[1],ciphertext_b64:params[2],generation:1};
          return {meta:{changes:1}};
        }
        if(sql.includes("UPDATE lbc_oauth_credentials")){
          if(!state.credentials || state.credentials.generation!==params[4])
            return {meta:{changes:0}};
          state.credentials={nonce_b64:params[0],ciphertext_b64:params[1],
            generation:state.credentials.generation+1};
          return {meta:{changes:1}};
        }
        if(sql.includes("INSERT OR IGNORE INTO lbc_graph_delta_cursor")){
          if(state.cursor)return {meta:{changes:0}};
          state.cursor={nonce_b64:params[1],ciphertext_b64:params[2],generation:1};
          return {meta:{changes:1}};
        }
        if(sql.includes("UPDATE lbc_graph_delta_cursor")){
          if(!state.cursor || state.cursor.generation!==params[4])
            return {meta:{changes:0}};
          state.cursor={nonce_b64:params[0],ciphertext_b64:params[1],
            generation:state.cursor.generation+1};
          return {meta:{changes:1}};
        }
        throw Error("unexpected_d1_run:"+sql);
      }
    }}}},
    async batch(statements){
      const result=[];
      for(const statement of statements){
        const {sql,params}=statement;
        const [owner,id,when]=params.slice(-3);
        const fenced=sql.includes("lbc_sync_lease WHERE owner_key");
        const leaseValid=!fenced || state.lock?.owner===owner &&
          state.lock?.id===id && state.lock.expiry>when;
        if(!leaseValid){result.push({meta:{changes:0}});continue}
        if(sql.includes("INSERT OR IGNORE INTO lbc_alert_messages")){
          const [messageId]=params;
          if(state.messages.has(messageId)){result.push({meta:{changes:0}});continue}
          state.messages.set(messageId,params);
          result.push({meta:{changes:1}});
        }else if(sql.includes("INSERT OR IGNORE INTO lbc_listing_observations")){
          const [messageId,listingId]=params;
          const key=messageId+"/"+listingId;
          if(!state.messages.has(messageId)||state.listings.has(key)){
            result.push({meta:{changes:0}});continue
          }
          state.listings.set(key,params);result.push({meta:{changes:1}});
        }else throw Error("unexpected_d1_batch:"+sql);
      }
      return result;
    }
  };
  return db;
}
test("full Outlook runner: encrypted credentials, token rotation, Graph identity, delta, D1 and replay",async()=>{
  const db=makeD1();
  const seed=await createD1OAuthStores({db,mailboxKey:OWNER,encryptionKey:OAUTH_KEY});
  await seed.credentialStore.save({refreshToken:"consented-token",accountId:"trusted-graph-id"});
  const env={DB:db,OUTLOOK_INGEST_ENABLED:"true",
    OUTLOOK_ENCRYPTION_KEY:OAUTH_KEY,OUTLOOK_DELTA_ENCRYPTION_KEY:DELTA_KEY,
    OUTLOOK_CLIENT_ID:CLIENT,OUTLOOK_CLIENT_SECRET:"fixture-secret",
    OUTLOOK_ALLOWED_SENDER_DOMAINS:"notifications.example.test",
    OUTLOOK_TENANT:"consumers"};
  const calls=[];
  let count=0;
  const fetchImpl=async(url,options)=>{
    calls.push(new URL(url).origin);
    if(url.startsWith("https://login.microsoftonline.com/")){
      const body=new URLSearchParams(options.body);
      assert.equal(body.get("refresh_token"),count===0?"consented-token":"rotated-token");
      return {ok:true,json:async()=>({access_token:"access",refresh_token:"rotated-token",expires_in:3600})};
    }
    if(url.startsWith("https://graph.microsoft.com/v1.0/me?")){
      assert.equal(options.headers.Authorization,"Bearer access");
      return {ok:true,json:async()=>({id:"trusted-graph-id"})};
    }
    assert.match(url,/\/mailFolders\/inbox\/messages\/delta/);
    assert.equal(options.headers.Authorization,"Bearer access");
    count++;
    return {ok:true,json:async()=>({value:count===1?[MAIL]:[],
      "@odata.deltaLink":CURSOR})};
  };
  const first=await runOutlookLeboncoinCollection({env,ownerKey:OWNER,fetchImpl,maxPages:2});
  assert.equal(first.status,"OK");
  assert.equal(first.inserted_listings,1);
  assert.equal(first.complete,true);
  assert.equal(db.state.messages.size,1);
  assert.equal(db.state.listings.size,1);
  assert.equal(db.state.lock,null);
  assert.equal(db.state.cursor.generation,1);
  const vault=await createD1OAuthStores({db,mailboxKey:OWNER,encryptionKey:OAUTH_KEY});
  assert.deepEqual(await vault.credentialStore.load(),{
    refreshToken:"rotated-token",accountId:"trusted-graph-id"
  });
  const second=await runOutlookLeboncoinCollection({env,ownerKey:OWNER,fetchImpl,maxPages:2});
  assert.equal(second.status,"EMPTY");
  assert.equal(second.inserted_listings,0);
  assert.equal(db.state.messages.size,1);
  assert.equal(db.state.listings.size,1);
  assert.equal(db.state.cursor.generation,2);
  assert.equal(db.state.lock,null);
  assert.equal(calls.filter(x=>x==="https://login.microsoftonline.com").length,2);
});
test("full runner rejects a different Graph identity before persisting any listing",async()=>{
  const db=makeD1();
  const vault=await createD1OAuthStores({db,mailboxKey:OWNER,encryptionKey:OAUTH_KEY});
  await vault.credentialStore.save({refreshToken:"initial",accountId:"expected-id"});
  const env={DB:db,OUTLOOK_INGEST_ENABLED:"true",OUTLOOK_ENCRYPTION_KEY:OAUTH_KEY,
    OUTLOOK_DELTA_ENCRYPTION_KEY:DELTA_KEY,OUTLOOK_CLIENT_ID:CLIENT,
    OUTLOOK_CLIENT_SECRET:"fixture-secret"};
  let deltaCalled=false;
  await assert.rejects(runOutlookLeboncoinCollection({env,ownerKey:OWNER,
    fetchImpl:async url=>{
      if(url.includes("login.microsoftonline.com"))
        return {ok:true,json:async()=>({access_token:"access",expires_in:3600})};
      if(url.includes("/v1.0/me?"))
        return {ok:true,json:async()=>({id:"different-id"})};
      deltaCalled=true;throw Error("unexpected_graph_delta");
    }
  }),/graph_identity_mismatch/);
  assert.equal(deltaCalled,false);
  assert.equal(db.state.messages.size,0);
  assert.equal(db.state.lock,null);
});
