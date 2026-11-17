import test from "node:test";
import assert from "node:assert/strict";
import { buildMarketDossiers } from "../market-dossier.mjs";
const row = (product_id, price_cents, observed_at) => ({product_id,price_cents,observed_at,price_kind:"AGGREGATE",currency:"EUR",source_url:"https://api.tcgdex.net/v2/fr/cards/base1-4"});
test("D1 export yields transparent dossiers, not fabricated investment theses",()=>{
 const result=buildMarketDossiers([{success:true,results:[row("card_a",1000,"2026-11-16T10:00:00Z"),row("card_a",1200,"2026-11-17T10:00:00Z"),row("card_b",800,"2026-11-17T10:00:00Z")]}],"2026-11-17T11:00:00Z");
 assert.equal(result.totalObservations,3);
 assert.equal(result.dossiers.length,2);
 assert.equal(result.dossiers[0].facts.indicativeChangePercent,20);
 assert.equal(result.dossiers[0].decision,"INVESTIGATE");
 assert.equal(result.dossiers[0].purchaseAuthorized,false);
 assert.equal(result.dossiers[0].entryHypothesis,null);
 assert.equal(result.dossiers[0].weakSignals.length,0);
 assert.ok(result.dossiers[0].evidenceGaps.includes("NO_COMPLETED_SALES_OR_VOLUME_EVIDENCE"));
});
test("rejects fake completed-sale data before building dossiers",()=>{
 assert.throws(()=>buildMarketDossiers([{success:true,results:[{...row("card_a",1000,"2026-11-17T10:00:00Z"),price_kind:"COMPLETED_SALE"}]}]),/unsupported_provenance/);
});
