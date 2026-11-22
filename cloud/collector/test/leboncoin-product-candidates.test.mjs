import test from "node:test";
import assert from "node:assert/strict";
import {discoverPackagedCandidates} from "../src/leboncoin-product-candidates.mjs";
const now=Date.parse("2026-11-20T10:00:00Z");
const key="etb:pokemon:evolving-skies:elite-trainer-box:fr:unlimited:u1:scelle";
const lot=(i,variant_key=key)=>({
  variant_key,lot_id:"gcc-0000000"+i+"-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  sold_day:"2026-11-15",price_cents:10000+i*1000,
  source_url:"https://gradedcardcenter.com/item/0000000"+i+"-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
});
test("real-shaped paid sales produce candidate, not verified product identity",()=>{
  const x=discoverPackagedCandidates([lot(1),lot(2),lot(3)],{now});
  assert.equal(x.status,"CANDIDATES_FOUND");
  assert.equal(x.candidates.length,1);
  assert.deepEqual(x.candidates[0],{
    status:"CANDIDATE_UNVERIFIED",variantKey:key,packaging:"etb",
    series:"evolving-skies",product:"elite-trainer-box",
    language:"fr",edition:"unlimited",units:1,paidLotCount:3,
    latestPaidDay:"2026-11-15",
    missingEvidence:["OFFICIAL_PRODUCT_REFERENCE","PACKAGING_AND_LOCALE_VERIFICATION",
      "REVIEWED_IDENTIFIERS","MATCHING_LISTING_ATTRIBUTES"]
  });
});
test("duplicates do not inflate paid-lot count",()=>{
  assert.equal(discoverPackagedCandidates([lot(1),lot(1),lot(2)],{now})
    .candidates[0].paidLotCount,2);
});
test("invalid URLs, prices, stale dates and unrecognized types are rejected",()=>{
  const invalid=[
    {...lot(1),source_url:"https://fake.example/paid"},
    {...lot(2),price_cents:0},
    {...lot(3),sold_day:"2025-01-01"},
    {...lot(4),sold_day:"2026-12-01"},
    {...lot(1),variant_key:"display:pokemon:evolving-skies:booster-box:fr:unlimited:u0:scelle"},
    {...lot(2),variant_key:"carte:pokemon:evolving-skies:215-203:umbreon-vmax:fr:unlimited:psa:10"}
  ];
  assert.deepEqual(discoverPackagedCandidates(invalid,{now}),{
    status:"NO_CANDIDATES",candidates:[]
  });
});
test("incomplete capped D1 results must never be called comprehensive",()=>{
  assert.deepEqual(discoverPackagedCandidates([lot(1),lot(2)],{now,maxRows:1}),{
    status:"SOURCE_UNAVAILABLE_OR_INCOMPLETE",candidates:[]
  });
  assert.deepEqual(discoverPackagedCandidates(null,{now}),{
    status:"SOURCE_UNAVAILABLE_OR_INCOMPLETE",candidates:[]
  });
});
test("ranking prioritizes supported paid lot count and recent dated evidence",()=>{
  const second="upc:pokemon:celebrations:ultra-premium-collection:fr:unlimited:u1:scelle";
  const rows=[lot(1,key),lot(2,key),lot(3,second)];
  assert.deepEqual(discoverPackagedCandidates(rows,{now}).candidates.map(x=>x.variantKey),
    [key,second]);
});
