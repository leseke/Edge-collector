import test from "node:test";
import assert from "node:assert/strict";
import { inspectObservations } from "../edge-readonly-tool.mjs";
import { assessMarket } from "../market-assessment.mjs";
const base = {product_id:"target",price_kind:"AGGREGATE",currency:"EUR",price_cents:1000,observed_at:"2026-11-17T10:00:00Z",source_url:"https://api.tcgdex.net/v2/fr/cards/base1-4"};
test("rejects deceptive source host suffix",()=>assert.throws(()=>inspectObservations([{...base,source_url:"https://api.tcgdex.net.evil.example/x"}],"target"),/untrusted_source/));
test("rejects embedded credentials and HTTP",()=>{
 for(const source_url of ["https://user:pass@api.tcgdex.net/x","http://api.tcgdex.net/x"])
   assert.throws(()=>inspectObservations([{...base,source_url}],"target"),/untrusted_source/);
});
test("rejects ambiguous observation timestamps",()=>assert.throws(()=>inspectObservations([{...base,observed_at:"tomorrow"}],"target"),/invalid_time/));
test("rejects future-dated observations as fresh market evidence",()=>{
 const result=assessMarket([{...base,observed_at:"2026-11-18T10:00:00Z"}],"target","2026-11-17T10:00:00Z");
 assert.ok(result.reasons.includes("FUTURE_DATED_OBSERVATION"));
 assert.equal(result.signal,"INSUFFICIENT_EVIDENCE");
});
