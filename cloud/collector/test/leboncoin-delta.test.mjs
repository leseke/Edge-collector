import test from "node:test";
import assert from "node:assert/strict";
import { syncLeboncoinDelta, validateGraphDeltaUrl, verifiedLeboncoinSender } from "../src/leboncoin-delta.mjs";
const NEXT="https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages/delta?$skiptoken=abc";
const DELTA="https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages/delta?$deltatoken=end";
const MAIL={id:"id1",subject:"Pokémon 30 ans : 990 nouveaux résultats",
  receivedDateTime:"2026-11-19T05:21:31Z",body:{contentType:"html",
    content:'<a href="https://www.leboncoin.fr/vi/3312500756.htm#email">Dracaufeu 160 € Paris</a>'}};
function makeDB() {
  const seen=new Set(),batches=[];
  return {batches,prepare(sql){return {bind(...args){
    if(sql.startsWith("SELECT 1"))return {first:async()=>seen.has(args[0])?{seen:1}:null};
    if(sql.startsWith("SELECT m.extracted_count"))return {first:async()=>(
      seen.has(args.at(-1))?{expected_count:1,actual_count:1,matching_count:1}:null)};
    return {sql,args};
  }}},async batch(stmts){seen.add(stmts[0].args[0]);batches.push(stmts);
    return stmts.map((_,i)=>({meta:{changes:i===stmts.length-1?0:1}}))}};
}
test("Graph delta URLs are pinned to Graph and message delta resource",()=>{
  assert.equal(validateGraphDeltaUrl(DELTA),DELTA);
  assert.throws(()=>validateGraphDeltaUrl("https://evil.example/token"),/unsafe_delta_cursor/);
  assert.throws(()=>validateGraphDeltaUrl("https://graph.microsoft.com/v1.0/me/drive/root"),/unsafe_delta_cursor/);
});
test("checkpoint saves only after successful persistence; safe resume after page cap",async()=>{
  const saved=[],db=makeDB();let cursor=null,requests=0;
  const store={load:async()=>cursor,save:async x=>{saved.push(x);cursor=x}};
  const fetchImpl=async url=>{
    requests++;
    if(url.includes("$skiptoken"))return {ok:true,json:async()=>({value:[], "@odata.deltaLink":DELTA})};
    return {ok:true,json:async()=>({value:[MAIL],"@odata.nextLink":NEXT})};
  };
  const a=await syncLeboncoinDelta({token:"fixture",db,cursorStore:store,fetchImpl,maxPages:1});
  assert.equal(a.status,"PARTIAL");
  assert.equal(a.inserted_listings,1);
  assert.deepEqual(saved,[NEXT]);
  const b=await syncLeboncoinDelta({token:"fixture",db,cursorStore:store,fetchImpl});
  assert.equal(b.complete,true);
  assert.deepEqual(saved,[NEXT,DELTA]);
  assert.equal(requests,2);
});
test("D1 write failure must not advance delta cursor",async()=>{
  let saved=0;
  const db=makeDB();db.batch=async()=>{throw new Error("db_down")};
  await assert.rejects(syncLeboncoinDelta({token:"fixture",db,
    cursorStore:{load:async()=>null,save:async()=>{saved++}},
    fetchImpl:async()=>({ok:true,json:async()=>({value:[MAIL],"@odata.deltaLink":DELTA})})}),/db_down/);
  assert.equal(saved,0);
});
test("does not silently reset expired Graph delta token",async()=>{
  const store={load:async()=>DELTA,save:async()=>{throw Error("must not save")}};
  await assert.rejects(syncLeboncoinDelta({token:"fixture",db:makeDB(),cursorStore:store,
    fetchImpl:async()=>({ok:false,status:410})}),/graph_delta_token_expired/);
});
test("rejects cross-origin continuation even when response is otherwise valid",async()=>{
  await assert.rejects(syncLeboncoinDelta({token:"fixture",db:makeDB(),
    cursorStore:{load:async()=>null,save:async()=>{}},
    fetchImpl:async()=>({ok:true,json:async()=>({value:[],"@odata.deltaLink":"https://example.com/stolen"})})}),
    /unsafe_delta_cursor/);
});

test("accepts documented Graph OData mailfolders('ID') delta continuation",async()=>{
  const canonical="https://graph.microsoft.com/v1.0/me/mailfolders('AQMkADNkNAAAgEMAAAA')/messages/delta?$skiptoken=opaque";
  assert.equal(validateGraphDeltaUrl(canonical),canonical);
  assert.throws(()=>validateGraphDeltaUrl("https://graph.microsoft.com/v1.0/me/mailfolders('abc')/drive/delta"),/unsafe_delta_cursor/);
  assert.throws(()=>validateGraphDeltaUrl("https://graph.microsoft.com/v1.0/me/mailfolders('abc%2Fusers')/messages/delta"),/unsafe_delta_cursor/);
});

test("lost lease between Graph fetch and persist never writes or checkpoints",async()=>{
  const db=makeDB();let saved=0,checks=0;
  await assert.rejects(syncLeboncoinDelta({
    token:"fixture",db,cursorStore:{load:async()=>null,save:async()=>{saved++}},
    assertActive:async()=>{if(++checks===2)throw Error("outlook_run_lease_lost")},
    fetchImpl:async()=>({ok:true,json:async()=>({value:[MAIL],"@odata.deltaLink":DELTA})})
  }),/outlook_run_lease_lost/);
  assert.equal(db.batches.length,0);
  assert.equal(saved,0);
});
test("lost lease after immutable write does not advance cursor",async()=>{
  const db=makeDB();let saved=0,checks=0;
  await assert.rejects(syncLeboncoinDelta({
    token:"fixture",db,cursorStore:{load:async()=>null,save:async()=>{saved++}},
    assertActive:async()=>{if(++checks===3)throw Error("outlook_run_lease_lost")},
    fetchImpl:async()=>({ok:true,json:async()=>({value:[MAIL],"@odata.deltaLink":DELTA})})
  }),/outlook_run_lease_lost/);
  assert.equal(db.batches.length,1);
  assert.equal(saved,0);
});

test("Graph sender allowlist rejects spoofed subject, lookalike domain and delegated sender",async()=>{
  const allowed=["notifications.example.test"];
  const from=address=>({emailAddress:{address}});
  const msg={from:from("alerts@notifications.example.test"),
    sender:from("alerts@notifications.example.test")};
  assert.equal(verifiedLeboncoinSender(msg,allowed),true);
  assert.equal(verifiedLeboncoinSender({...msg,from:from("alerts@evil.test")},allowed),false);
  assert.equal(verifiedLeboncoinSender({...msg,from:from("alerts@notifications.example.test.evil.test")},allowed),false);
  assert.equal(verifiedLeboncoinSender({...msg,sender:from("forwarder@evil.test")},allowed),false);
  assert.equal(verifiedLeboncoinSender({...msg,from:null},allowed),false);
  assert.throws(()=>verifiedLeboncoinSender(msg,["example.test,evil.test"]),/invalid_outlook_sender_allowlist/);
});
test("unapproved sender is ignored before D1 insert, but Graph cursor still advances",async()=>{
  const db=makeDB(),saved=[];
  const forged={...MAIL,from:{emailAddress:{address:"attacker@evil.test"}}};
  const result=await syncLeboncoinDelta({
    token:"fixture",db,
    allowedSenderDomains:["notifications.example.test"],
    cursorStore:{load:async()=>null,save:async url=>saved.push(url)},
    fetchImpl:async()=>({ok:true,json:async()=>({value:[forged],"@odata.deltaLink":DELTA})})
  });
  assert.equal(result.status,"EMPTY");
  assert.equal(result.inserted_listings,0);
  assert.equal(result.matching_alerts,0);
  assert.equal(db.batches.length,0);
  assert.deepEqual(saved,[DELTA]);
});
test("approved Graph sender is ingested and keeps listing unverified",async()=>{
  const db=makeDB();
  const authentic={...MAIL,
    from:{emailAddress:{address:"alerts@notifications.example.test"}},
    sender:{emailAddress:{address:"alerts@notifications.example.test"}}};
  const result=await syncLeboncoinDelta({
    token:"fixture",db,allowedSenderDomains:["notifications.example.test"],
    cursorStore:{load:async()=>null,save:async()=>{}},
    fetchImpl:async()=>({ok:true,json:async()=>({value:[authentic],"@odata.deltaLink":DELTA})})
  });
  assert.equal(result.inserted_listings,1);
  assert.equal(result.matching_alerts,1);
});

test("archived incomplete email blocks Graph delta checkpoint instead of disappearing",async()=>{
  let saves=0,batches=0;
  const db={
    prepare(sql){return {bind(){return {
      async first(){
        if(sql.startsWith("SELECT 1 AS seen"))return {seen:1};
        if(sql.startsWith("SELECT m.extracted_count"))
          return {expected_count:1,actual_count:0,matching_count:0};
        throw Error("unexpected_sql");
      }
    }}}},
    async batch(){batches++;throw Error("must_not_write")}
  };
  await assert.rejects(syncLeboncoinDelta({
    token:"fixture",db,cursorStore:{load:async()=>null,save:async()=>{saves++}},
    fetchImpl:async()=>({ok:true,json:async()=>({value:[MAIL],"@odata.deltaLink":DELTA})})
  }),/outlook_existing_message_incomplete_or_changed/);
  assert.equal(saves,0);
  assert.equal(batches,0);
});
