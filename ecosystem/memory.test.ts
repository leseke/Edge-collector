import { test } from "node:test";
import { strict as assert } from "node:assert";
import { remember, recall, type MemoryEntry, type MemoryStore } from "./memory";
function store():MemoryStore {
 const rows=new Map<string,MemoryEntry>();
 return {async append(e){const old=rows.get(e.id);if(old){if(JSON.stringify(old)!==JSON.stringify(e))throw new Error("conflict");return "duplicate";}rows.set(e.id,structuredClone(e));return "inserted";},async get(id){return structuredClone(rows.get(id)??null);},async timeline(subject,before,limit){return [...rows.values()].filter(e=>e.subject===subject&&e.recordedAt<=before).sort((a,b)=>b.recordedAt-a.recordedAt||a.id.localeCompare(b.id)).slice(0,limit).map(e=>structuredClone(e));}};
}
const observation:MemoryEntry={id:"o",subject:"p",kind:"observation",recordedAt:10,occurredAt:9,statement:"Observed listing",sourceUrl:"https://example.com/listing",evidenceIds:[]};
const hypothesis:MemoryEntry={id:"h",subject:"p",kind:"hypothesis",recordedAt:20,occurredAt:20,statement:"Demand may rise",evidenceIds:["o"]};
test("observation and hypothesis are recalled as of a historical date",async()=>{const s=store();await remember(s,observation,10);await remember(s,hypothesis,20);assert.deepEqual((await recall(s,"p",15)).map(e=>e.id),["o"]);});
test("missing evidence is rejected",async()=>{await assert.rejects(remember(store(),hypothesis,20));});
test("future evidence cannot support an earlier hypothesis",async()=>{const s=store();await remember(s,{...observation,recordedAt:30},30);await assert.rejects(remember(s,hypothesis,30));});
test("outcome requires a previously recorded hypothesis",async()=>{const s=store();await remember(s,observation,10);await remember(s,hypothesis,20);const o:MemoryEntry={id:"r",subject:"p",kind:"outcome",recordedAt:30,occurredAt:30,statement:"Inconclusive",evidenceIds:["o"],hypothesisId:"h",outcome:"inconclusive"};assert.equal(await remember(s,o,30),"inserted");await assert.rejects(remember(s,{...o,id:"bad",occurredAt:15},30));});
test("duplicates do not overwrite memory",async()=>{const s=store();await remember(s,observation,10);assert.equal(await remember(s,observation,10),"duplicate");await assert.rejects(remember(s,{...observation,statement:"changed"},10));});
test("observation requires a valid source",async()=>{await assert.rejects(remember(store(),{...observation,sourceUrl:undefined},10));});
