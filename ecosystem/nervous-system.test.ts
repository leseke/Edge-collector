import { test } from "node:test";
import { strict as assert } from "node:assert";
import { tick, type NervousState, type Signal } from "./nervous-system";
const initial: NervousState = {resources:{capacity:100,available:100,reserve:20,refillPerMs:1,updatedAt:0,pending:[]},seen:{},inbox:[]};
const costs = {collect:10,verify:10,archive:5,analyze:20};
const signal = (id:string,kind:Signal["kind"]="listing.observed"):Signal => ({id,kind,subject:"catalog-item",observedAt:0,expiresAt:100});
test("observations route to archive and verification, never directly to AI",()=>{
 const a=tick(initial,[signal("one")],0,costs);
 assert.deepEqual(a.admitted.map(j=>j.kind),["archive","verify"]);
 assert.equal(tick(a.state,[signal("one")],1,costs).admitted.length,0);
});
test("only verified evidence triggers analysis",()=>{
 assert.deepEqual(tick(initial,[signal("v","evidence.verified")],0,costs).admitted.map(j=>j.kind),["archive","analyze"]);
 assert.deepEqual(tick(initial,[signal("r","evidence.rejected")],0,costs).admitted.map(j=>j.kind),["archive"]);
});
test("expired signals do not execute",()=>assert.deepEqual(tick(initial,[signal("old")],100,costs).rejected,["old"]));
test("capacity pressure preserves unprocessed signals",()=>{
 const a=tick(initial,[signal("one"),signal("two")],0,costs,1);
 assert.equal(a.state.inbox.length,1);
 assert.equal(a.processed.length,1);
});
test("resource pressure defers jobs",()=>{
 const a=tick({...initial,resources:{...initial.resources,available:5}},[signal("v","evidence.verified")],0,costs);
 assert.deepEqual(a.admitted.map(j=>j.kind),["archive"]);
 assert.deepEqual(a.deferred.map(j=>j.kind),["analyze"]);
});
