import test from "node:test";
import assert from "node:assert/strict";
import { createDeepSeekAdapter } from "../deepseek-adapter.mjs";
import { runInvestigations } from "../investigation-pipeline.mjs";
const row={product_id:"card_a",price_kind:"AGGREGATE",currency:"EUR",source_url:"https://api.tcgdex.net/v2/fr/cards/base1-4",observed_at:"2026-11-17T10:00:00Z",price_cents:1000};
const payload=[{success:true,results:[row]}];
test("provider disabled by default and requires explicit credentials",()=>{
 assert.throws(()=>createDeepSeekAdapter({apiKey:"secret"}),/model_disabled/);
 assert.throws(()=>createDeepSeekAdapter({enabled:true}),/model_key_missing/);
 assert.throws(()=>createDeepSeekAdapter({enabled:true,apiKey:"secret",maxTokens:10000}),/invalid_token_budget/);
 assert.throws(()=>createDeepSeekAdapter({enabled:true,apiKey:"secret",model:"other"}),/model_not_allowlisted/);
});
test("real adapter contract with mocked transport reaches independent review",async()=>{
 let calls=0;
 const generate=createDeepSeekAdapter({enabled:true,apiKey:"secret",fetchImpl:async(url,init)=>{
  calls++;
  assert.equal(url,"https://api.deepseek.com/chat/completions");
  assert.equal(init.method,"POST");
  assert.equal(init.headers.Authorization,"Bearer secret");
  const req=JSON.parse(init.body);
  assert.equal(req.max_tokens,800);
  assert.equal(req.response_format.type,"json_object");
  const brief=JSON.parse(req.messages[1].content);
  const [sourceUrl,observedAt]=brief.sourceReferences[0].split("|");
  const proposal={productId:brief.productId,thesis:"Unverified preshot",catalysts:["Potential collector interest"],risks:["Liquidity unknown"],entryHypothesis:"Only investigate possible entry",exitHypothesis:"Reassess after one year",evidence:[{kind:"FACT",claim:"Indicative aggregate exists",sourceUrl,observedAt},{kind:"BET",claim:"Demand may emerge"}],purchaseAuthorized:true};
  return {ok:true,text:async()=>JSON.stringify({choices:[{message:{content:JSON.stringify(proposal)}}]})};
 }});
 const result=await runInvestigations(payload,generate,{now:"2026-11-17T11:00:00Z"});
 assert.equal(calls,1);
 assert.equal(result.results[0].status,"PROPOSAL_REQUIRES_HUMAN_REVIEW");
 assert.equal(result.results[0].review.purchaseAuthorized,false);
 assert.equal(result.results[0].review.claimSemanticsVerified,false);
});
test("provider errors fail closed without leaking keys or response text",async()=>{
 const generate=createDeepSeekAdapter({enabled:true,apiKey:"top-secret",fetchImpl:async()=>({ok:false,status:401,text:async()=>"top-secret"})});
 const result=await runInvestigations(payload,generate);
 assert.equal(result.results[0].status,"FAILED_CLOSED");
 assert.ok(!JSON.stringify(result).includes("top-secret"));
});
