import {test} from "node:test";
import {strict as assert} from "node:assert";
import {commercialVariations} from "./commercial-variation";
import type {MemoryEntry,MemoryStore} from "./memory";
function row(id:string,updated:number,price:number,overrides:Record<string,unknown>={}):MemoryEntry{
 return {id,subject:"pokemon_card_base1-4",kind:"observation",occurredAt:updated+100,recordedAt:updated+200,sourceUrl:"https://api.tcgdex.net/v2/fr/cards/base1-4",evidenceIds:[],statement:JSON.stringify({schema:"edge.ecosystem.commercial.v1",priceKind:"indicative",currency:"EUR",marketLanguage:"UNKNOWN",marketLanguageVerified:false,source:"Cardmarket indication via TCGdex",snapshotId:id,priceMinor:price,sourceUpdatedAt:new Date(updated).toISOString(),...overrides})};
}
function store(rows:MemoryEntry[]):MemoryStore{return {async append(){throw Error("read only");},async get(id){return rows.find(r=>r.id===id)??null;},async timeline(subject,before){return rows.filter(r=>r.subject===subject&&r.recordedAt<=before);}};}
const a=row("1-1",1000,1000),b=row("2-1",2000,1250),subject=a.subject;
test("comparable updated aggregate produces evidence-linked variation only",async()=>{const r=await commercialVariations(store([a,b]),subject,3000);assert.equal(r.length,1);assert.equal(r[0].changeMinor,250);assert.equal(r[0].changePercent,25);assert.equal(r[0].previousEvidenceId,a.id);assert.equal(r[0].currentEvidenceId,b.id);assert.equal(r[0].executionAllowed,false);assert.equal(r[0].independentlyVerified,false);});
test("repeated source timestamp does not create new market movement",async()=>{assert.deepEqual(await commercialVariations(store([a,row("2-1",1000,1000)]),subject,3000),[]);});
test("contradictory values at identical source timestamp are not compared",async()=>{assert.deepEqual(await commercialVariations(store([a,b,row("3-1",2000,1400)]),subject,3000),[]);});
test("different price types and sources cannot establish variation",async()=>{for(const other of [row("2-1",2000,1250,{priceKind:"declared_sale"}),row("2-1",2000,1250,{source:"other"}),row("2-1",2000,1250,{currency:"USD"}),row("2-1",2000,1250,{marketLanguageVerified:true})])assert.deepEqual(await commercialVariations(store([a,other]),subject,3000),[]);});
test("future knowledge and unchanged prices produce no movement",async()=>{assert.deepEqual(await commercialVariations(store([a,b]),subject,2100),[]);assert.deepEqual(await commercialVariations(store([a,row("2-1",2000,1000)]),subject,3000),[]);});
