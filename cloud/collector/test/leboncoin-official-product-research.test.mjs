import test from "node:test";
import assert from "node:assert/strict";
import {officialPokemonResearchSources,officialResearchForCandidate}
  from "../src/leboncoin-official-product-research.mjs";
import {discoverPackagedCandidates} from "../src/leboncoin-product-candidates.mjs";
const now=Date.parse("2026-11-20T11:00:00Z");
const key="etb:pokemon:prismatic-evolutions:elite-trainer-box:en:unlimited:u1:scelle";
const lot={variant_key:key,lot_id:"gcc-00000001-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  sold_day:"2026-11-19",price_cents:5999,
  source_url:"https://gradedcardcenter.com/item/00000001-aaaa-4aaa-8aaa-aaaaaaaaaaaa"};
test("official references are authentic product-gallery URLs, not unverified variant approvals",()=>{
  assert.ok(officialPokemonResearchSources.length>=3);
  for(const item of officialPokemonResearchSources){
    assert.equal(item.referenceStatus,"OFFICIAL_PRODUCT_PAGE_ONLY");
    assert.match(item.sourceUrl,/^https:\/\/www\.pokemon\.com\/us\/pokemon-tcg\/product-gallery\//);
    assert.equal(Object.hasOwn(item,"variantKey"),false);
  }
});
test("candidate with exact English release can receive manufacturer research link only",()=>{
  const candidate=discoverPackagedCandidates([lot],{now}).candidates[0];
  assert.equal(candidate.status,"CANDIDATE_UNVERIFIED");
  const found=officialResearchForCandidate(candidate);
  assert.equal(found.length,1);
  assert.equal(found[0].status,"RESEARCH_LEAD_ONLY");
  assert.match(found[0].sourceUrl,/prismatic-evolutions-elite-trainer-box$/);
  assert.equal(Object.hasOwn(found[0],"reviewStatus"),false);
});
test("French or different series cannot inherit English official product reference",()=>{
  const candidate=discoverPackagedCandidates([lot],{now}).candidates[0];
  assert.deepEqual(officialResearchForCandidate({...candidate,language:"fr"}),[]);
  assert.deepEqual(officialResearchForCandidate({...candidate,series:"celebrations"}),[]);
  assert.deepEqual(officialResearchForCandidate({...candidate,packaging:"upc"}),[]);
});
test("untrusted or arbitrary candidate status never unlocks reference association",()=>{
  const candidate=discoverPackagedCandidates([lot],{now}).candidates[0];
  assert.deepEqual(officialResearchForCandidate({...candidate,status:"VERIFIED"}),[]);
  assert.deepEqual(officialResearchForCandidate(null),[]);
  assert.deepEqual(officialResearchForCandidate(candidate,[{
    productFamily:"ETB",series:candidate.series,sourceLocale:"us-en",
    canonicalName:"Bad",referenceStatus:"OFFICIAL_PRODUCT_PAGE_ONLY",
    sourceUrl:"https://attacker.example/fake"
  }]),[]);
});
