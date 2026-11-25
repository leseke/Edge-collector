import test from "node:test";
import assert from "node:assert/strict";
import {exactGtin,comparableOffers,philibertCandidates} from "../src/commercial-parser.mjs";
const row={gtin:"4006381333931",fresh:true,status:"READ",currency:"EUR",priceCents:1000,availability:"InStock",merchant:"Playin"};
test("valid codes canonicalize and invalid checksums are rejected",()=>{
 assert.equal(exactGtin(row.gtin),"04006381333931");
 assert.equal(exactGtin("4006381333932"),null);
});
test("compares distinct merchants with same code and stock class",()=>{
 const [group]=comparableOffers([row,{...row,merchant:"Philibert",priceCents:800}]);
 assert.equal(group.spreadCents,200);
 assert.equal(group.offers[0].merchant,"Philibert");
 for(const other of [{...row},{...row,merchant:"Philibert",fresh:false},{...row,merchant:"Philibert",availability:"PreOrder"},{...row,merchant:"Philibert",currency:"USD"},{...row,merchant:"Philibert",gtin:"96385074"}])assert.deepEqual(comparableOffers([row,other]),[]);
});
test("only accepted Philibert product routes are extracted",()=>{
 assert.equal(philibertCandidates('<a href="/fr/magic/123-example-4006381333931.html">Example sealed collection</a>').length,1);
 assert.deepEqual(philibertCandidates('<a href="https://example.org/fr/magic/123-example-4006381333931.html">Example sealed collection</a>'),[]);
});

test("same merchant duplicates retain the cheapest valid offer regardless of order",()=>{
 const cheaper={...row,priceCents:700},other={...row,merchant:"Philibert",priceCents:900};
 for(const input of [[row,cheaper,other],[cheaper,row,other]]){
 const [g]=comparableOffers(input);assert.equal(g.spreadCents,200);assert.equal(g.offers[0].priceCents,700);assert.equal(g.offers.length,2);
 }
});
