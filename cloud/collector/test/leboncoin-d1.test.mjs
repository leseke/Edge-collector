import test from "node:test";
import assert from "node:assert/strict";
import {parseLeboncoinAlert} from "../src/leboncoin-email.mjs";
import {persistLeboncoinAlerts,validateAlert} from "../src/leboncoin-d1.mjs";

const sample = () => parseLeboncoinAlert({
  id:"mail-1",subject:"Pokémon ME6 : 38 nouveaux résultats",
  receivedDateTime:"2026-11-19T05:21:31Z",
  body:{content:"| [\nLot ETB Pokémon\n75 €\nÉvreux 27000\n](https://www.leboncoin.fr/vi/3312468604.htm#tracking)"}
});
test("validates listing provenance and blocks forged completed sales",()=>{
  const a=sample();
  assert.equal(a.listings.length,1);
  assert.equal(a.listings[0].price_cents,7500);
  assert.doesNotThrow(()=>validateAlert(a));
  a.listings[0].price_kind="COMPLETED_SALE";
  assert.throws(()=>validateAlert(a),/invalid_lbc_listing/);
});
test("rejects hostile listing URLs",()=>{
  const a=sample();
  a.listings[0].source_url="https://evil.example/steal";
  assert.throws(()=>validateAlert(a),/invalid_lbc_listing/);
});
test("uses one atomic batch and skips previously processed messages",async()=>{
  const calls=[],seen=new Set();
  const db={
    prepare(sql){
      return {
        bind(...params){
          if (sql.startsWith("SELECT 1")) return {first:async()=>seen.has(params[0])?{seen:1}:null};
          return {sql,params};
        }
      };
    },
    async batch(statements){
      calls.push(statements);
      const mail=statements[0].params[0];
      seen.add(mail);
      return statements.map((_,i)=>({meta:{changes:i===statements.length-1?0:1}}));
    }
  };
  const first=await persistLeboncoinAlerts(db,[sample()]);
  assert.deepEqual(first,{inserted_messages:1,inserted_listings:1,already_seen_messages:0});
  assert.equal(calls.length,1);
  assert.match(calls[0][1].sql,/INSERT OR IGNORE/);
  const second=await persistLeboncoinAlerts(db,[sample()]);
  assert.equal(second.already_seen_messages,1);
  assert.equal(calls.length,1);
});
test("rejects invalid clock before writing",async()=>{
  const db={prepare:()=>({bind:()=>({first:async()=>null})}),batch:async()=>{throw Error("should not write")}};
  await assert.rejects(persistLeboncoinAlerts(db,[sample()],{clock:()=>"invalid"}),/invalid_clock/);
});
