import test from "node:test";
import assert from "node:assert/strict";
import { prepareInvestigationBrief } from "../agent-brief.mjs";
const payload=[{success:true,results:[{product_id:"card_a",price_kind:"AGGREGATE",currency:"EUR",source_url:"https://api.tcgdex.net/v2/fr/cards/base1-4",observed_at:"2026-11-17T10:00:00Z",price_cents:1000}]}];
test("agent receives only scoped source references and indicative aggregates",()=>{
 const result=prepareInvestigationBrief(payload,"card_a","2026-11-17T11:00:00Z");
 assert.equal(result.task,"PROPOSE_PRESHOT_INVESTIGATION");
 assert.equal(result.sourceReferences.length,1);
 assert.equal(result.purchaseAuthorized,false);
 assert.ok(result.missingEvidence.includes("NO_COMPLETED_SALES_OR_VOLUME_EVIDENCE"));
});
test("unknown product cannot access other product data",()=>assert.throws(()=>prepareInvestigationBrief(payload,"card_b"),/unknown_product/));
