import test from "node:test";
import assert from "node:assert/strict";
import { normalizeD1Export } from "../export-d1.mjs";
const row = { product_id:"pokemon_card_base1_4",price_kind:"AGGREGATE",currency:"EUR",source_url:"https://api.tcgdex.net/v2/fr/cards/base1-4",observed_at:"2026-11-17T12:00:00Z",price_cents:1200 };
test("trusted D1 result becomes a minimal, read-only snapshot",()=>{
 const output=normalizeD1Export([{success:true,results:[{...row,payload_sha256:"not-for-agent"}]}]);
 assert.equal(output.length,1);
 assert.equal(output[0].price_cents,1200);
 assert.equal("payload_sha256" in output[0],false);
});
test("rejects failed or unverifiable exports",()=>{
 assert.throws(()=>normalizeD1Export([{success:false,results:[]}]),/invalid_d1_export/);
 assert.throws(()=>normalizeD1Export([{success:true,results:[{...row,price_kind:"COMPLETED_SALE"}]}]),/unsupported_provenance/);
});
