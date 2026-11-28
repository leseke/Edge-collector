import { test } from "node:test";
import { strict as assert } from "node:assert";
import { regulate, type Ecosystem, type Job } from "./regulator";
const initial: Ecosystem = {capacity:100,available:50,reserve:20,refillPerMs:1,updatedAt:0,pending:[]};
const job = (id:string,kind:Job["kind"],cost:number,dueAt=0):Job => ({id,kind,cost,dueAt,priority:1});
test("protect reserve for essential work",()=>{
 const result=regulate(initial,0,[job("a","analyze",35),job("b","collect",20)]);
 assert.deepEqual(result.admitted.map(j=>j.id),["b"]);
 assert.equal(result.state.available,30);
 assert.equal(result.deferred.length,1);
});
test("refill admits deferred work once",()=>{
 const a=regulate(initial,0,[job("a","analyze",40)]);
 const b=regulate(a.state,20,[job("a","analyze",40)]);
 assert.equal(b.admitted.length,1);
 assert.equal(b.state.available,30);
 assert.equal(b.state.pending.length,0);
});
test("future work is deferred",()=>assert.equal(regulate(initial,0,[job("a","verify",1,10)]).admitted.length,0));
test("reject invalid costs and reversed clocks",()=>{
 assert.throws(()=>regulate(initial,0,[job("a","collect",-1)]));
 assert.throws(()=>regulate(initial,-1));
});
