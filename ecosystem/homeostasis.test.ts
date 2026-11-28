import { test } from "node:test";
import { strict as assert } from "node:assert";
import { cycle, acknowledge, type CycleInput, type CycleState, type CyclePolicy } from "./homeostasis";
import type { MemoryEntry, MemoryStore } from "./memory";
function memory():MemoryStore{
 const rows=new Map<string,MemoryEntry>();
 return {async get(id){return rows.get(id)??null;},async append(e){const old=rows.get(e.id);if(old){if(JSON.stringify(old)!==JSON.stringify(e))throw new Error("conflict");return "duplicate";}rows.set(e.id,e);return "inserted";},async timeline(subject,before,limit){return [...rows.values()].filter(e=>e.subject===subject&&e.recordedAt<=before).slice(0,limit);}};
}
const state:CycleState={nervous:{resources:{capacity:100,available:100,reserve:20,refillPerMs:1,updatedAt:0,pending:[]},seen:{},inbox:[]},outstanding:[]};
const p:CyclePolicy={costs:{collect:10,verify:10,archive:5,analyze:20},ttlMs:1000,marketWindowMs:1000,adaptation:{windowMs:1000,minSamples:5,minIntervalMs:10,maxIntervalMs:1000}};
const empty:CycleInput={observations:[],previous:[],references:[],signals:[],marketSignals:[],channels:[],feedback:[]};
const observation={id:"a",source:"market",listingId:"listing",subject:"product",observedAt:1,priceMinor:100,currency:"EUR",language:"FR",condition:"sealed",url:"https://example.com/listing",priceKind:"asking" as const};
test("observation is remembered and verification scheduled",async()=>{const s=memory();const r=await cycle(state,{...empty,observations:[observation]},s,10,p);assert.equal(r.verdicts[0].status,"accepted");assert.ok(await s.get(JSON.stringify(["observation","a"])));assert.deepEqual(r.state.outstanding.map(j=>j.kind),["archive","verify"]);});
test("outstanding work survives next cycle until acknowledged",async()=>{const s=memory();const r=await cycle(state,{...empty,observations:[observation]},s,10,p);const next=await cycle(r.state,empty,s,11,p);assert.equal(next.state.outstanding.length,2);assert.equal(acknowledge(next.state,next.state.outstanding[0].id).outstanding.length,1);});
test("invalid observation is not promoted to market evidence",async()=>{const s=memory();const r=await cycle(state,{...empty,observations:[{...observation,priceMinor:-1}]},s,10,p);assert.equal(r.verdicts[0].status,"rejected");assert.equal(await s.get(JSON.stringify(["observation","a"])),null);assert.deepEqual(r.state.outstanding.map(j=>j.kind),["archive"]);});
test("unbacked market signals cannot produce leads",async()=>{const r=await cycle(state,{...empty,marketSignals:[{id:"s",subject:"product",family:"demand",sourceGroup:"a",eventKey:"x",evidenceId:"missing",recordedAt:1,direction:"positive",strength:1,verified:true}]},memory(),10,p);assert.deepEqual(r.leads,[]);});
test("observation alone cannot establish verified market signal",async()=>{const r=await cycle(state,{...empty,observations:[observation],marketSignals:[{id:"s",subject:"product",family:"demand",sourceGroup:"a",eventKey:"x",evidenceId:JSON.stringify(["observation","a"]),recordedAt:10,direction:"positive",strength:1,verified:true}]},memory(),10,p);assert.equal(r.leads[0].verifiedCount,0);assert.equal(r.leads[0].executionAllowed,false);});
