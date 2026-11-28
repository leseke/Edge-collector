import { test } from "node:test";
import { strict as assert } from "node:assert";
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import { D1Memory, D1Checkpoints, type Database, type Statement } from "./d1-store";
import { remember } from "./memory";
import { JobLeases } from "./job-lease";
import type { MemoryEntry } from "./memory";
import type { CycleState } from "./homeostasis";
function database(){
 const sqlite=new DatabaseSync(":memory:");
 sqlite.exec("PRAGMA foreign_keys=ON");
 for(const f of ["memory.sql","checkpoint.sql","job-lease.sql","job-result.sql"])sqlite.exec(readFileSync("ecosystem/"+f,"utf8"));
 type V=string|number|null;
 class Query implements Statement{
  constructor(readonly sql:string,readonly args:V[]=[]){}
  bind(...args:V[]){return new Query(this.sql,args);}
  async first<T>(){return (sqlite.prepare(this.sql).get(...this.args)??null) as T|null;}
  async all<T>(){return {success:true,results:sqlite.prepare(this.sql).all(...this.args) as T[]};}
  execute(){return {success:true,meta:{changes:Number(sqlite.prepare(this.sql).run(...this.args).changes)}};}
  async run(){return this.execute();}
 }
 const db:Database={prepare:s=>new Query(s),async batch(statements){sqlite.exec("BEGIN");try{const result=statements.map(s=>(s as Query).execute());sqlite.exec("COMMIT");return result;}catch(e){sqlite.exec("ROLLBACK");throw e;}}};
 return {db,sqlite};
}
const entry:MemoryEntry={id:"o",subject:"p",kind:"observation",recordedAt:10,occurredAt:9,statement:"test",sourceUrl:"https://example.com",evidenceIds:[]};
const state:CycleState={nervous:{resources:{capacity:100,available:80,reserve:20,refillPerMs:1,updatedAt:10,pending:[]},seen:{},inbox:[]},outstanding:[{id:"j",kind:"verify",cost:10,priority:90,dueAt:10}]};
test("memory survives adapter reconstruction and refuses conflicting ID",async()=>{const {db,sqlite}=database();try{await remember(new D1Memory(db),entry,10);const m=new D1Memory(db);assert.equal((await m.get("o"))?.statement,"test");assert.equal(await m.append(entry),"duplicate");await assert.rejects(m.append({...entry,statement:"changed"}));}finally{sqlite.close();}});
test("failed evidence insertion rolls back the whole batch",async()=>{const {db,sqlite}=database();try{const m=new D1Memory(db);await assert.rejects(m.append({...entry,id:"h",kind:"hypothesis",evidenceIds:["missing"]}));assert.equal(await m.get("h"),null);}finally{sqlite.close();}});
test("immutable records cannot be updated or deleted through SQL",async()=>{const {db,sqlite}=database();try{await new D1Memory(db).append(entry);assert.throws(()=>sqlite.exec("UPDATE ecosystem_memory SET statement='changed'"));assert.throws(()=>sqlite.exec("DELETE FROM ecosystem_memory"));}finally{sqlite.close();}});
test("checkpoint restores outstanding tasks and rejects stale concurrent writes",async()=>{const {db,sqlite}=database();try{const a=new D1Checkpoints(db),b=new D1Checkpoints(db);assert.equal(await a.save("edge",null,state,10),true);assert.equal(await b.save("edge",null,state,10),false);assert.deepEqual(await b.load("edge"),{version:0,state});assert.equal(await a.save("edge",0,state,11),true);assert.equal(await b.save("edge",0,{...state,outstanding:[]},12),false);assert.deepEqual(await b.load("edge"),{version:1,state});}finally{sqlite.close();}});

test("simultaneous claims admit only one active owner",async()=>{const {db,sqlite}=database();try{const a=new JobLeases(db),b=new JobLeases(db);const claims=await Promise.all([a.claim("edge","j","a",10,100),b.claim("edge","j","b",10,100)]);assert.equal(claims.filter(Boolean).length,1);assert.equal(await b.claim("edge","j","c",109,100),false);}finally{sqlite.close();}});
test("expired lease can be recovered and stale owner cannot complete",async()=>{const {db,sqlite}=database();try{const a=new JobLeases(db),b=new JobLeases(db);assert.equal(await a.claim("edge","j","a",10,20),true);assert.equal(await a.complete("edge","j","a",30),false);assert.equal(await b.claim("edge","j","b",30,20),true);assert.equal(await a.complete("edge","j","a",31),false);assert.equal(await b.complete("edge","j","b",31),true);assert.equal(await a.claim("edge","j","c",100,20),false);}finally{sqlite.close();}});
test("completed jobs cannot be completed twice or reclaimed",async()=>{const {db,sqlite}=database();try{const l=new JobLeases(db);await l.claim("edge","j","a",10,20);assert.equal(await l.complete("edge","j","a",11),true);assert.equal(await l.complete("edge","j","a",12),false);assert.equal(await l.claim("edge","j","b",100,20),false);}finally{sqlite.close();}});
test("leases are scoped by ecosystem and job identity",async()=>{const {db,sqlite}=database();try{const l=new JobLeases(db);assert.equal(await l.claim("edge","j","a",10,20),true);assert.equal(await l.claim("other","j","b",10,20),true);assert.equal(await l.claim("edge","k","c",10,20),true);}finally{sqlite.close();}});
test("invalid lease duration and completion without ownership are rejected",async()=>{const {db,sqlite}=database();try{const l=new JobLeases(db);await assert.rejects(l.claim("edge","j","a",10,0));assert.equal(await l.complete("edge","j","a",10),false);await l.claim("edge","j","b",10,20);assert.equal(await l.complete("edge","j","a",11),false);}finally{sqlite.close();}});

test("result and completion are committed together and replay is harmless",async()=>{const {db,sqlite}=database();try{const l=new JobLeases(db);await l.claim("edge","j","a",10,20);assert.equal(await l.completeWithResult("edge","j","a",11,'{"value":1}'),true);assert.equal(await l.completeWithResult("edge","j","a",12,'{"value":2}'),false);assert.equal(await l.claim("edge","j","b",40,20),false);assert.equal(sqlite.prepare("SELECT result_json FROM ecosystem_job_result").get()?.result_json,'{"value":1}');assert.equal(sqlite.prepare("SELECT completed_at FROM ecosystem_job_lease").get()?.completed_at,11);}finally{sqlite.close();}});
test("expired or superseded owners cannot publish results",async()=>{const {db,sqlite}=database();try{const l=new JobLeases(db);await l.claim("edge","j","a",10,20);assert.equal(await l.completeWithResult("edge","j","a",30,"{}"),false);await l.claim("edge","j","b",30,20);assert.equal(await l.completeWithResult("edge","j","a",31,"{}"),false);assert.equal(await l.completeWithResult("edge","j","b",31,"{}"),true);}finally{sqlite.close();}});
test("invalid JSON cannot mark a task complete",async()=>{const {db,sqlite}=database();try{const l=new JobLeases(db);await l.claim("edge","j","a",10,20);await assert.rejects(l.completeWithResult("edge","j","a",11,"invalid"));assert.equal(sqlite.prepare("SELECT completed_at FROM ecosystem_job_lease").get()?.completed_at,null);assert.equal(await l.completeWithResult("edge","j","a",12,"{}"),true);}finally{sqlite.close();}});
test("stored results are immutable",async()=>{const {db,sqlite}=database();try{const l=new JobLeases(db);await l.claim("edge","j","a",10,20);await l.completeWithResult("edge","j","a",11,"{}");assert.throws(()=>sqlite.exec("UPDATE ecosystem_job_result SET result_json='null'"));assert.throws(()=>sqlite.exec("DELETE FROM ecosystem_job_result"));}finally{sqlite.close();}});
