import test from "node:test";
import assert from "node:assert/strict";
import {handleOutlookOffers,renderOutlookOffers} from "../src/leboncoin-offers-http.mjs";

const ORIGIN="https://edge.example.com";
const PATH="/internal/outlook/offers";
const LISTING_ID="leboncoin:3312500756";
const ROW={listing_id:LISTING_ID,source_url:"https://www.leboncoin.fr/vi/3312500756.htm",
  title:"Dracaufeu 30 ans",price_cents:16000,location:"Paris",
  search_name:"Pokémon 30 ans",observed_at:"2026-11-20T07:00:00Z",
  alert_hits:2,advertised_count:1286,extracted_count:5,
  first_price_cents:17000,first_observed_at:"2026-11-19T07:00:00Z"};
const env={
  OUTLOOK_ROUTES_ENABLED:"true",OUTLOOK_OFFERS_ENABLED:"true",
  OUTLOOK_REDIRECT_URI:ORIGIN+"/auth/microsoft/callback",
  CF_ACCESS_TEAM_DOMAIN:"https://edge-team.cloudflareaccess.com",
  CF_ACCESS_APP_AUD:"edge-audience-1234",
  CF_ACCESS_ALLOWED_SUBJECTS:"one-approved-operator",
  DB:{prepare(){return {all:async()=>({results:[ROW]})}}}
};
const verified=async()=>({authenticated:true,ownerKey:"a".repeat(64)});
const req=(suffix=PATH,init={})=>new Request(ORIGIN+suffix,init);
test("no routes or offers opt-in hides all data and does not call D1 or Access",async()=>{
  for(const key of ["OUTLOOK_ROUTES_ENABLED","OUTLOOK_OFFERS_ENABLED"]){
    let queries=0,verifications=0;
    const res=await handleOutlookOffers({
      request:req(),env:{...env,[key]:"false",DB:{prepare(){queries++;throw Error("D1")}}},
      verifySession:async()=>{verifications++;throw Error("Access")}
    });
    assert.equal(res.status,404);assert.equal(queries,0);assert.equal(verifications,0);
  }
});
test("signed operator is required and query, alternate headers and non-GET fail closed",async()=>{
  for(const request of [
    req(PATH+"?limit=500"),
    req(PATH,{method:"POST"}),
    req(PATH,{headers:{Authorization:"Bearer something"}}),
    req(PATH,{headers:{"X-Owner-Key":"attacker"}}),
    new Request("https://attacker.example"+PATH)
  ]){
    const res=await handleOutlookOffers({request,env,verifySession:async()=>{
      throw Error("must_not_verify");
    }});
    assert.equal(res.status,404);
  }
  const anonymous=await handleOutlookOffers({request:req(),env,
    verifySession:async()=>{throw Error("invalid_access_identity")}});
  assert.equal(anonymous.status,404);
});
test("signed operator reads limited private D1 observations with provenance",async()=>{
  let queries=0;
  const res=await handleOutlookOffers({
    request:req(),env:{...env,DB:{prepare(sql){
      queries++;
      if(sql.includes("lbc_listing_observations")){
        assert.match(sql,/LIMIT 50/);
        assert.match(sql,/PARTITION BY o\.listing_id/);
        assert.match(sql,/WHERE rn=1/);
        assert.match(sql,/FIRST_VALUE\(o.price_cents\)/);
        return {all:async()=>({results:[ROW]})};
      }
      assert.match(sql,/paid_market_sales/);
      return {bind:()=>({all:async()=>({results:[]})})};
    }}},
    verifySession:verified,now:()=>Date.parse("2026-11-20T08:00:00Z")
  });
  assert.equal(res.status,200);assert.equal(queries,2);
  const html=await res.text();
  assert.match(html,/Dracaufeu 30 ans/);
  assert.match(html,/160,00/);
  assert.match(html,/MOINS DE 24 H/);
  assert.match(html,/2 alerte\(s\) distincte\(s\)/);
  assert.match(html,/5 extraits sur 1286 résultats annoncés/);
  assert.match(html,/Prix signalé initialement/);
  assert.match(html,/170,00/);
  assert.match(html,/−10,00|-10,00/);
  assert.match(html,/Premier signalement/);
  assert.match(html,/Prix demandé extrait/);
  assert.match(html,/Ventes payées comparables non établies/);
  assert.match(html,/https:\/\/www\.leboncoin\.fr\/vi\/3312500756\.htm/);
  assert.doesNotMatch(html,/COMPLETED_SALE|Vente confirmée/);
  assert.equal(res.headers.get("cache-control"),"no-store, private");
});
test("malicious titles and fake ad URLs cannot execute script or become clickable",()=>{
  const html=renderOutlookOffers([
    {...ROW,title:'<img src=x onerror="alert(1)">',search_name:"A & B"},
    {...ROW,listing_id:"leboncoin:3312500757",source_url:"https://evil.example/link"}
  ],{now:Date.parse("2026-11-20T08:00:00Z")});
  assert.match(html,/&lt;img src=x onerror=&quot;alert\(1\)&quot;&gt;/);
  assert.doesNotMatch(html,/<img src=x/);
  assert.doesNotMatch(html,/https:\/\/evil\.example/);
  assert.match(html,/A &amp; B/);
});
test("unavailable D1 fails with generic private error, not secrets",async()=>{
  const res=await handleOutlookOffers({request:req(),env:{
    ...env,DB:{prepare(){throw Error("private-db-secret")}}
  },verifySession:verified});
  assert.equal(res.status,503);
  assert.equal((await res.text()).includes("private-db-secret"),false);
});
test("empty D1 feed states no imported offers, never fabricated examples",async()=>{
  const html=renderOutlookOffers([]);
  assert.match(html,/Aucune annonce importée/);
  assert.doesNotMatch(html,/Dracaufeu 30 ans/);
});

test("private offers HTML prioritizes price-drop investigations above one-off sightings",()=>{
  const now=Date.parse("2026-11-20T08:00:00Z");
  const unseen={...ROW,listing_id:"leboncoin:3312500758",
    source_url:"https://www.leboncoin.fr/vi/3312500758.htm",
    title:"Simple observation",alert_hits:1,
    first_price_cents:15000,price_cents:15000};
  const recurred={...ROW,listing_id:"leboncoin:3312500759",
    source_url:"https://www.leboncoin.fr/vi/3312500759.htm",
    title:"Annonce répétée",alert_hits:2,
    first_price_cents:16000,price_cents:16000};
  const html=renderOutlookOffers([unseen,recurred,ROW],{now});
  assert.ok(html.indexOf("Dracaufeu 30 ans")<html.indexOf("Annonce répétée"));
  assert.ok(html.indexOf("Annonce répétée")<html.indexOf("Simple observation"));
  assert.match(html,/data-signal="PRICE_DROP"/);
  assert.match(html,/data-signal="REPEATED"/);
  assert.match(html,/data-signal="OBSERVED"/);
});

test("strict complete variant and 3 paid GCC sales reveal dated median, not a BUY status",async()=>{
  const key="carte:pokemon:evolving-skies:215-203:umbreon-vmax:fr:unlimited:psa:10";
  const title="Carte Pokémon Evolving Skies 215/203 Umbreon VMAX Français Unlimited PSA 10";
  const sales=[20000,25000,30000].map((price,i)=>{
    const id="gcc-0000000"+(i+1)+"-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
    return {variant_key:key,lot_id:id,sold_day:"2026-11-15",price_cents:price,
      source_url:"https://gradedcardcenter.com/item/"+id.slice(4)};
  });
  const db={prepare(sql){
    if(sql.includes("lbc_listing_observations"))
      return {all:async()=>({results:[{...ROW,title}]})};
    assert.match(sql,/paid_market_sales/);
    return {bind:()=>({all:async()=>({results:sales})})};
  }};
  const res=await handleOutlookOffers({
    request:req(),env:{...env,DB:db},verifySession:verified,
    now:()=>Date.parse("2026-11-20T10:00:00Z")
  });
  assert.equal(res.status,200);
  const html=await res.text();
  assert.match(html,/3 transactions \/ 90 jours/);
  assert.match(html,/Médiane brute : 250,00/);
  assert.match(html,/Bas observé : 200,00/);
  assert.match(html,/Écart brut avec le bas des ventes : 40,00/);
  assert.match(html,/hors frais, livraison et risque de variante/);
  assert.doesNotMatch(html,/ACHETER|BUY|rendement garanti/i);
});
