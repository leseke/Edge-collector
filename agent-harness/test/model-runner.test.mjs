import test from "node:test";
import assert from "node:assert/strict";
import { main } from "../run-model-investigations.mjs";
import { runInvestigations } from "../investigation-pipeline.mjs";
const row=(product_id)=>({product_id,price_kind:"AGGREGATE",currency:"EUR",source_url:"https://api.tcgdex.net/v2/fr/cards/base1-4",observed_at:"2026-11-17T10:00:00Z",price_cents:1000});
test("paid runner fails before reading files without two explicit opt-ins",async()=>{
 await assert.rejects(main({env:{},argv:["node","runner","nonexistent.json"]}),/paid_model_not_enabled/);
 await assert.rejects(main({env:{EDGE_ENABLE_PAID_MODEL:"YES",DEEPSEEK_API_KEY:"secret"},argv:["node","runner","nonexistent.json"]}),/model_data_transfer_not_authorized/);
 await assert.rejects(main({env:{EDGE_ENABLE_PAID_MODEL:"YES",EDGE_ALLOW_MODEL_DATA_TRANSFER:"YES"},argv:["node","runner","nonexistent.json"]}),/model_key_missing/);
});
test("paid runner rejects invalid call budgets before touching the file",async()=>{
 const env={EDGE_ENABLE_PAID_MODEL:"YES",EDGE_ALLOW_MODEL_DATA_TRANSFER:"YES",DEEPSEEK_API_KEY:"secret",EDGE_MAX_MODEL_CALLS:"6"};
 await assert.rejects(main({env,argv:["node","runner","nonexistent.json"]}),/invalid_model_call_budget/);
});
test("per-run product limit preserves exact cursor and prevents extra model invocations",async()=>{
 const data=[{success:true,results:[row("card_a"),row("card_b"),row("card_c")]}];
 let calls=0;
 const first=await runInvestigations(data,async()=>{calls++;throw Error("simulated provider failure")},{maxProducts:1,cursor:0});
 assert.equal(calls,1);
 assert.equal(first.processedProducts,1);
 assert.equal(first.remainingProducts,2);
 assert.equal(first.nextCursor,1);
 await assert.rejects(runInvestigations(data,async()=>{}, {maxProducts:21}),/invalid_product_limit/);
});
