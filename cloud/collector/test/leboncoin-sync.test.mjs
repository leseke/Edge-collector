import test from "node:test";
import assert from "node:assert/strict";
import { syncOutlookLeboncoin } from "../src/leboncoin-sync.mjs";

const message = {
  id:"m-1",subject:"Pokémon 30 ans : 990 nouveaux résultats",
  receivedDateTime:"2026-11-19T05:21:31Z",
  body:{content:"| [\nDracaufeu\n160 €\nParis\n](https://www.leboncoin.fr/vi/3312500756.htm)"}
};
function dbFixture() {
  const seen = new Set(),stored=[];
  return {
    stored,
    prepare(sql) {
      return { bind(...args) {
        if (sql.startsWith("SELECT 1")) return {first:async()=>seen.has(args[0])?{seen:1}:null};
        if (sql.startsWith("SELECT m.extracted_count"))return {first:async()=>(
          seen.has(args[0])?{expected_count:1,actual_count:1}:null)};
        return {sql,args};
      }};
    },
    async batch(statements) {
      seen.add(statements[0].args[0]);
      stored.push(statements);
      return statements.map((_,i)=>({meta:{changes:i===statements.length-1?0:1}}));
    }
  };
}
test("sync reports actual extracted rows separately from alert advertised totals",async()=>{
  const db=dbFixture();
  const fetchImpl=async()=>({ok:true,json:async()=>({value:[message]})});
  const options={token:"offline-fixture",db,fetchImpl,clock:()=> "2026-11-19T11:00:00Z"};
  const one=await syncOutlookLeboncoin(options);
  assert.equal(one.status,"OK");
  assert.equal(one.advertised_results_sum,990);
  assert.equal(one.unique_listing_ids,1);
  assert.equal(one.inserted_messages,1);
  assert.equal(one.inserted_listings,1);
  const two=await syncOutlookLeboncoin(options);
  assert.equal(two.already_seen_messages,1);
  assert.equal(two.inserted_listings,0);
  assert.equal(db.stored.length,1);
});
test("no credential means no Graph request nor DB writes",async()=>{
  const db=dbFixture();
  await assert.rejects(syncOutlookLeboncoin({token:"",db,fetchImpl:async()=>{throw Error("network");}}),/missing_graph_token/);
  assert.equal(db.stored.length,0);
});
