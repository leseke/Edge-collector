import test from "node:test";
import assert from "node:assert/strict";
import {PRODUCT_IDENTITY_SCHEMA_VERSION,reviewedPackagedProducts,
  catalogVariantForListing} from "../src/leboncoin-product-identities.mjs";
import {comparablePaidSales} from "../src/leboncoin-paid-comparables.mjs";
const now=Date.parse("2026-11-20T10:00:00Z");
const key="etb:pokemon:evolving-skies:elite-trainer-box:fr:unlimited:u1:scelle";
const title="1 ETB Pokémon Evolving Skies Elite Trainer Box Français Unlimited scellée ref 123456";
const verified={version:PRODUCT_IDENTITY_SCHEMA_VERSION,variantKey:key,
  reviewStatus:"VERIFIED",officialSource:"https://www.pokemon.com/fr/jcc-pokemon",
  verifiedOn:"2026-11-20",identifiers:["elite trainer box","ref 123456"]};
const sale=(n,price,variant_key=key)=>{
  const lot_id="gcc-0000000"+n+"-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
  return {variant_key,lot_id,sold_day:"2026-11-15",price_cents:price,
    source_url:"https://gradedcardcenter.com/item/"+lot_id.slice(4)};
};
test("production catalog is intentionally unpopulated before external review",()=>{
  assert.deepEqual(reviewedPackagedProducts,[]);
  assert.equal(catalogVariantForListing(title,[key]),null);
  assert.equal(comparablePaidSales(title,[sale(1,3000),sale(2,4000),sale(3,5000)],now).status,
    "NO_VERIFIED_VARIANT");
});
test("reviewed complete ETB identity matches only explicit listing evidence",()=>{
  assert.equal(catalogVariantForListing(title,[key],[verified]),key);
  for(const notExact of [
    "1 ETB Pokémon Evolving Skies Elite Trainer Box Français Unlimited scellée",
    "1 ETB Pokémon Evolving Skies Elite Trainer Box Français scellée ref 123456",
    "1 ETB Pokémon Evolving Skies Elite Trainer Box Unlimited scellée ref 123456",
    "1 ETB Pokémon Evolving Skies Elite Trainer Box Français Unlimited ref 123456",
    "Lot de 2 ETB Pokémon Evolving Skies Elite Trainer Box Français Unlimited scellée ref 123456",
    "1 UPC Pokémon Evolving Skies Elite Trainer Box Français Unlimited scellée ref 123456"
  ])assert.equal(catalogVariantForListing(notExact,[key],[verified]),null,notExact);
});
test("ETB enables paid comparisons only with three actual unique eligible GCC lots",()=>{
  const rows=[sale(1,7000),sale(2,8000),sale(3,9000)];
  assert.deepEqual(comparablePaidSales(title,rows,now,[verified]),{
    status:"COMPARABLE",variant:key,saleCount:3,medianCents:8000,lowCents:7000
  });
  assert.equal(comparablePaidSales(title,rows.slice(0,2),now,[verified]).status,
    "INSUFFICIENT_PAID_SALES");
});
test("unapproved, old-schema or off-domain records cannot turn asking prices into sales evidence",()=>{
  for(const entry of [
    {...verified,reviewStatus:"CANDIDATE"},
    {...verified,version:2},
    {...verified,officialSource:"https://example.com/fake"},
    {...verified,identifiers:["elite trainer box"]},
    {...verified,identifiers:["elite trainer box","elite trainer box"]},
    {...verified,variantKey:"etb:pokemon:evolving-skies:elite-trainer-box:fr:unlimited:u0:scelle"}
  ])assert.equal(catalogVariantForListing(title,[key],[entry]),null);
});
test("display, UPC and coffret have distinct reviewed identities and explicit package quantities",()=>{
  const examples=[
    ["display:pokemon:evolving-skies:booster-box:fr:unlimited:u36:scelle",
      "36 unités Display Pokémon Evolving Skies Booster Box Français Unlimited scellé ref 4321",
      ["booster box","ref 4321"]],
    ["upc:pokemon:celebrations:ultra-premium-collection:fr:unlimited:u1:scelle",
      "1 UPC Pokémon Celebrations Ultra Premium Collection Français Unlimited scellée ref 5678",
      ["ultra premium collection","ref 5678"]],
    ["coffret:pokemon:celebrations:collection-pikachu:fr:unlimited:u1:scelle",
      "1 coffret Pokémon Celebrations Collection Pikachu Français Unlimited scellé ref 8765",
      ["collection pikachu","ref 8765"]]
  ];
  for(const [variantKey,description,identifiers] of examples){
    const entry={...verified,variantKey,identifiers};
    assert.equal(catalogVariantForListing(description,[variantKey],[entry]),variantKey);
    assert.equal(catalogVariantForListing(description.replace(/scellée?|scelle/,"ouvert"),[variantKey],[entry]),null);
  }
});
test("ambiguous reviewed identities cannot be resolved by choosing a cheap sale",()=>{
  const another="etb:pokemon:evolving-skies:elite-trainer-box:en:unlimited:u1:scelle";
  const record={...verified,variantKey:another};
  assert.equal(catalogVariantForListing(title+" English",[key,another],[verified,record]),null);
});
