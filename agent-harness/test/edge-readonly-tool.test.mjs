import test from "node:test";
import assert from "node:assert/strict";
import { inspectObservations } from "../edge-readonly-tool.mjs";
const row = (date, price) => ({product_id:"pokemon_card_base1_4",price_kind:"AGGREGATE",currency:"EUR",source_url:"https://api.tcgdex.net/v2/fr/cards/base1-4",observed_at:date,price_cents:price});
test("calculates price delta from real-shaped records without inventing sales",()=>{
 const result=inspectObservations([row("2026-11-17T10:00:00Z",1000),row("2026-11-18T10:00:00Z",1100)],"pokemon_card_base1_4");
 assert.equal(result.changePercent,10);
 assert.equal(result.provenance,"INDICATIVE_AGGREGATE_NOT_COMPLETED_SALE");
 assert.equal(result.purchaseAuthorized,false);
});
test("does not fabricate data when missing",()=>{
 const result=inspectObservations([],"pokemon_card_base1_4");
 assert.equal(result.latest,null);assert.equal(result.changePercent,null);
});
test("rejects untrusted source and unsupported sale classifications",()=>{
 assert.throws(()=>inspectObservations([{...row("2026-11-17T10:00:00Z",1000),source_url:"https://evil.example"}],"pokemon_card_base1_4"),/untrusted_source/);
 assert.throws(()=>inspectObservations([{...row("2026-11-17T10:00:00Z",1000),price_kind:"COMPLETED_SALE"}],"pokemon_card_base1_4"),/unsupported_provenance/);
});
