import test from "node:test";
import assert from "node:assert/strict";
import { reviewInvestigation } from "../investigation-review.mjs";
const row={product_id:"card_a",price_kind:"AGGREGATE",currency:"EUR",source_url:"https://api.tcgdex.net/v2/fr/cards/base1-4",observed_at:"2026-11-17T10:00:00Z",price_cents:1000};
const exportData=[{success:true,results:[row]}];
const proposal={productId:"card_a",thesis:"Possible preshot with unconfirmed demand",catalysts:["Future release (hypothesis)"],risks:["Low liquidity"],entryHypothesis:"Investigate under 10 EUR, not a quote",exitHypothesis:"Review in twelve months",evidence:[{kind:"FACT",claim:"A TCGdex aggregate observation exists",sourceUrl:row.source_url,observedAt:row.observed_at},{kind:"BET",claim:"Collector interest may increase"}]};
test("verified source provenance does not become verified demand",()=>{
 const result=reviewInvestigation(proposal,exportData,"2026-11-17T11:00:00Z");
 assert.equal(result.status,"PROPOSAL_REQUIRES_HUMAN_REVIEW");
 assert.equal(result.evidence.facts.length,1);
 assert.equal(result.evidence.bets.length,1);
 assert.equal(result.modelClaimsVerified,true);
 assert.equal(result.demandConfirmed,false);
 assert.equal(result.purchaseAuthorized,false);
});
test("model cannot invent an external factual citation",()=>{
 const forged={...proposal,evidence:[{kind:"FACT",claim:"Unverified sold listing",sourceUrl:"https://example.com/sale",observedAt:row.observed_at}]};
 const result=reviewInvestigation(forged,exportData,"2026-11-17T11:00:00Z");
 assert.equal(result.status,"NEEDS_EVIDENCE_CORRECTION");
 assert.equal(result.modelClaimsVerified,false);
 assert.equal(result.evidence.unsupportedFacts.length,1);
});
test("model cannot use a product absent from trusted D1",()=>{
 assert.throws(()=>reviewInvestigation({...proposal,productId:"other"},exportData),/product_not_in_trusted_snapshot/);
});
