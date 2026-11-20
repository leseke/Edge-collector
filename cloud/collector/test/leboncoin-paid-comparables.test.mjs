import test from "node:test";
import assert from "node:assert/strict";
import {verifiedSaleVariantForListing,comparablePaidSales} from "../src/leboncoin-paid-comparables.mjs";
const now=Date.parse("2026-11-20T10:00:00Z");
const key="carte:pokemon:evolving-skies:215-203:umbreon-vmax:fr:unlimited:psa:10";
const title="Carte Pokémon Evolving Skies 215/203 Umbreon VMAX Français Unlimited PSA 10";
const lot=n=>"gcc-"+["00000001","00000002","00000003","00000004"][n]+"-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const sale=(i,price)=>({variant_key:key,lot_id:lot(i),sold_day:"2026-11-15",
  price_cents:price,source_url:"https://gradedcardcenter.com/item/"+lot(i).slice(4)});
test("requires all concrete series number name language printing and grade",()=>{
  assert.equal(verifiedSaleVariantForListing(title,[key,key]),key);
  for(const weak of [
    "Umbreon VMAX PSA 10",
    "Pokémon Evolving Skies Umbreon VMAX PSA 10 Français Unlimited",
    "Pokémon Evolving Skies 215/203 Umbreon VMAX Unlimited PSA 10",
    "Pokémon Evolving Skies 215/203 Umbreon VMAX Français Unlimited PSA 9",
    "Pokémon Evolving Skies 215/203 Umbreon VMAX Français PSA 10",
    "Pokémon Fusion Strike 215/203 Umbreon VMAX Français Unlimited PSA 10"
  ])assert.equal(verifiedSaleVariantForListing(weak,[key]),null,weak);
});
test("three distinct eligible GCC paid sales support a dated median and observed low",()=>{
  const result=comparablePaidSales(title,[sale(0,20000),sale(1,25000),sale(2,30000)],now);
  assert.deepEqual(result,{status:"COMPARABLE",variant:key,saleCount:3,
    medianCents:25000,lowCents:20000});
});
test("do not claim comparables from one sale, invalid links or duplicated lot ID",()=>{
  assert.equal(comparablePaidSales(title,[sale(0,20000)],now).status,"INSUFFICIENT_PAID_SALES");
  assert.equal(comparablePaidSales(title,[sale(0,20000),sale(0,25000),sale(1,30000)],now).status,"INSUFFICIENT_PAID_SALES");
  assert.equal(comparablePaidSales(title,[sale(0,20000),sale(1,25000),{...sale(2,30000),
    source_url:"https://other.example/fake"}],now).status,"INSUFFICIENT_PAID_SALES");
  assert.equal(comparablePaidSales("Umbreon", [sale(0,20000),sale(1,25000),sale(2,30000)],now).status,"NO_VERIFIED_VARIANT");
});
test("reject future and stale paid sales",()=>{
  assert.equal(comparablePaidSales(title,[
    sale(0,20000),sale(1,25000),{...sale(2,30000),sold_day:"2026-12-01"}
  ],now).status,"INSUFFICIENT_PAID_SALES");
  assert.equal(comparablePaidSales(title,[
    sale(0,20000),sale(1,25000),{...sale(2,30000),sold_day:"2025-05-01"}
  ],now).status,"INSUFFICIENT_PAID_SALES");
});
test("ambiguous exact-variant matches are rejected instead of choosing cheaper reference",()=>{
  const another="carte:pokemon:evolving-skies:215-203:umbreon-vmax:en:unlimited:psa:10";
  assert.equal(verifiedSaleVariantForListing(title+" English",[key,another]),null);
});

const sealedKey="booster:pokemon:tempete-argentee:lugia:fr:unlimited:scelle";
const boxKey="coffret:pokemon:celebrations:collection-pikachu:fr:unlimited:scelle";
test("exact single sealed booster with full set name language and printing supports paid comparables",()=>{
  const name="1 booster Pokémon Tempête Argentée Lugia Français Unlimited scellé";
  assert.equal(verifiedSaleVariantForListing(name,[sealedKey]),sealedKey);
  const sales=[2000,2700,3100].map((price,i)=>({...sale(i,price),variant_key:sealedKey}));
  assert.deepEqual(comparablePaidSales(name,sales,now),{
    status:"COMPARABLE",variant:sealedKey,saleCount:3,medianCents:2700,lowCents:2000
  });
});
test("exact named sealed coffret can match three paid sales, never a bare brand label",()=>{
  const name="Coffret Pokémon Celebrations Collection Pikachu Français Unlimited scellé";
  assert.equal(verifiedSaleVariantForListing(name,[boxKey]),boxKey);
  const sales=[4000,4900,6000].map((price,i)=>({...sale(i,price),variant_key:boxKey}));
  assert.equal(comparablePaidSales(name,sales,now).medianCents,4900);
});
test("reject booster lots, displays, unsealed, unknown language, missing edition, or wrong product",()=>{
  for(const title of [
    "Booster Pokémon Tempête Argentée Lugia Français Unlimited scellé",
    "Lot de 12 booster Pokémon Tempête Argentée Lugia Français Unlimited scellé",
    "Display 1 booster Pokémon Tempête Argentée Lugia Français Unlimited scellé",
    "1 booster Pokémon Tempête Argentée Lugia Unlimited scellé",
    "1 booster Pokémon Tempête Argentée Lugia Français scellé",
    "1 booster Pokémon Tempête Argentée Lugia Français Unlimited",
    "1 booster Pokémon Tempête Argentée Gengar Français Unlimited scellé"
  ])assert.equal(verifiedSaleVariantForListing(title,[sealedKey]),null,title);
  assert.equal(verifiedSaleVariantForListing(
    "Coffret Pokémon Celebrations Collection Pikachu Français Unlimited",
    [boxKey]),null);
  assert.equal(verifiedSaleVariantForListing(
    "Lot de coffrets Pokémon Celebrations Collection Pikachu Français Unlimited scellé",
    [boxKey]),null);
});
test("conflicting exact sealed variants remain ambiguous",()=>{
  const en="booster:pokemon:tempete-argentee:lugia:en:unlimited:scelle";
  assert.equal(verifiedSaleVariantForListing(
    "1 booster Pokémon Tempête Argentée Lugia Français English Unlimited scellé",
    [sealedKey,en]),null);
});
