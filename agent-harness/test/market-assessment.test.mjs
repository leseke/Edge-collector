import test from "node:test";
import assert from "node:assert/strict";
import { assessMarket } from "../market-assessment.mjs";
const row = (day, price) => ({ product_id:"card_a",price_kind:"AGGREGATE",currency:"EUR",source_url:"https://api.tcgdex.net/v2/fr/cards/base1-4",observed_at:day,price_cents:price });
test("a 50% indicative jump does not become confirmed demand or an order",()=>{
 const result=assessMarket([row("2026-11-16T10:00:00Z",1000),row("2026-11-17T10:00:00Z",1500)],"card_a","2026-11-17T11:00:00Z");
 assert.equal(result.indicativeChangePercent,50);
 assert.equal(result.signal,"INSUFFICIENT_EVIDENCE");
 assert.equal(result.demandConfirmed,false);
 assert.equal(result.purchaseAuthorized,false);
 assert.equal(result.opportunityRejected,false);
});
test("empty observations remain eligible for preshot hypothesis but not a purchase",()=>{
 const result=assessMarket([],"card_a","2026-11-17T11:00:00Z");
 assert.equal(result.latestIndicativePriceCents,null);
 assert.ok(result.reasons.includes("NO_OBSERVATIONS"));
 assert.equal(result.hypothesisAllowed,true);
});
test("stale data is labeled explicitly",()=>{
 const result=assessMarket([row("2026-11-01T10:00:00Z",1000)],"card_a","2026-11-17T11:00:00Z");
 assert.ok(result.reasons.includes("STALE_OR_MISSING_OBSERVATION"));
});
