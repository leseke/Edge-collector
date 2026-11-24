import test from "node:test";
import assert from "node:assert/strict";
import {productOffer} from "../src/commercial-offer.mjs";
const html=x=>'<script type="application/ld+json">'+JSON.stringify(x)+'</script>';
const p={"@type":"Product",name:"Fixture",sku:"X",offers:{"@type":"Offer",price:"29.90",priceCurrency:"EUR",availability:"https://schema.org/PreOrder"}};
test("extracts explicit offer and preorder",()=>assert.deepEqual(productOffer(html(p)),{gtin:null,name:"Fixture",sku:"X",priceCents:2990,currency:"EUR",availability:"PreOrder"}));
test("does not choose ambiguous offers",()=>assert.equal(productOffer(html({...p,offers:[p.offers,p.offers]})).priceCents,null));
test("rejects multiple products",()=>assert.equal(productOffer(html([p,p])),null));
test("missing currency is unknown",()=>assert.equal(productOffer(html({...p,offers:{...p.offers,priceCurrency:null}})).priceCents,null));

test("extracts valid GTIN and rejects conflicting identifiers",()=>{
 assert.equal(productOffer(html({...p,gtin13:"4006381333931"})).gtin,"04006381333931");
 assert.equal(productOffer(html({...p,gtin13:"4006381333932"})).gtin,null);
 assert.equal(productOffer(html({...p,gtin13:"4006381333931",gtin8:"96385074"})).gtin,null);
});
