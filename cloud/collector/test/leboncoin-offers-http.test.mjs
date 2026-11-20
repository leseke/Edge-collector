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
      assert.match(sql,/lbc_listing_observations/);
      assert.match(sql,/LIMIT 50/);
      assert.match(sql,/PARTITION BY o\.listing_id/);
      assert.match(sql,/WHERE rn=1/);
      assert.match(sql,/FIRST_VALUE\(o.price_cents\)/);
      return {all:async()=>({results:[ROW]})};
    }}},
    verifySession:verified,now:()=>Date.parse("2026-11-20T08:00:00Z")
  });
  assert.equal(res.status,200);assert.equal(queries,1);
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
