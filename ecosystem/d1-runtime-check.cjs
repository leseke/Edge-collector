const {createRequire}=require("node:module");
const {readFileSync}=require("node:fs");
const {resolve}=require("node:path");
const assert=require("node:assert/strict");
const {randomUUID}=require("node:crypto");
console.log("[D1] Loading Miniflare");
const {Miniflare}=createRequire(resolve(process.env.EDGE_VALIDATION_PREFIX,"package.json"))("miniflare");
console.log("[D1] Loading compiled ecosystem modules");
const compiled=process.env.EDGE_COMPILED;
const {D1Memory,D1Checkpoints}=require(resolve(compiled,"d1-store.js"));
const {JobLeases}=require(resolve(compiled,"job-lease.js"));
const {executeExternal}=require(resolve(compiled,"external-operation.js"));
const {RecoveryStore}=require(resolve(compiled,"recovery-store.js"));
const {dispatchRead}=require(resolve(compiled,"persistent-dispatcher.js"));
(async()=>{
 console.log("[D1] Starting isolated runtime");
 const mf=new Miniflare({modules:true,script:"export default {fetch(){return new Response('test')}}",compatibilityDate:"2026-02-05",d1Databases:{DB:randomUUID()}});
 try{
  console.log("[D1] Acquiring binding");
  const db=await mf.getD1Database("DB");
  assert.equal((await db.prepare("SELECT 1 AS ok").first()).ok,1);
  console.log("[D1] Binding responds to SELECT 1");
  for(const name of ["memory","checkpoint","job-lease","job-result","recovery-state","dispatch-lock","external-operation"]){
   // D1 exec accepts one statement per line; keep complete trigger bodies on one line.
   const sql=readFileSync("ecosystem/"+name+".sql","utf8").replace(/^--.*$/gm,"");
   const statements=sql.match(/CREATE TRIGGER[\s\S]*?END;|CREATE (?:TABLE|INDEX)[\s\S]*?;/gi)||[];
   assert.ok(statements.length,name);
   for(const [i,statement] of statements.entries()){
    console.log(`[D1] Migration ${name} statement ${i+1}/${statements.length}`);
    const result=await db.prepare(statement).run();
    assert.equal(result.success,true,`migration ${name} statement ${i+1}`);
   }
  }
  console.log("[D1] Memory and transaction rollback");
  const memory=new D1Memory(db);
  const observation={id:"o",subject:"p",kind:"observation",recordedAt:10,occurredAt:9,statement:"test fixture",sourceUrl:"https://example.com",evidenceIds:[]};
  assert.equal(await memory.append(observation),"inserted");
  assert.equal(await memory.append(observation),"duplicate");
  await assert.rejects(memory.append({...observation,id:"bad",kind:"hypothesis",evidenceIds:["missing"]}));
  assert.equal(await memory.get("bad"),null);
  console.log("[D1] Versioned checkpoints");
  const checkpoints=new D1Checkpoints(db);
  const state={nervous:{resources:{capacity:100,available:80,reserve:20,refillPerMs:1,updatedAt:10,pending:[]},seen:{},inbox:[]},outstanding:[]};
  assert.equal(await checkpoints.save("test",null,state,10),true);
  assert.equal(await checkpoints.save("test",null,state,10),false);
  assert.deepEqual((await checkpoints.load("test")).state,state);
  console.log("[D1] Job leases and result ledger");
  const leases=new JobLeases(db);
  assert.equal((await Promise.all([leases.claim("test","j","a",10,20),leases.claim("test","j","b",10,20)])).filter(Boolean).length,1);
  assert.equal(await leases.claim("test","j","c",30,20),true);
  assert.equal(await leases.completeWithResult("test","j","a",31,"{}"),false);
  assert.equal(await leases.completeWithResult("test","j","c",31,"{}"),true);
  console.log("[D1] External deduplication");
  const q={scope:"test",id:"external",fingerprint:"fixture",token:"a"};
  let calls=0;const invoke=async()=>{calls++;return "{}";};
  assert.equal((await executeExternal(db,q,()=>10,invoke)).status,"completed");
  assert.equal((await executeExternal(db,{...q,token:"b"},()=>11,invoke)).status,"cached");
  assert.equal(calls,1);
  console.log("[D1] Persistent dispatch");
  const store=new RecoveryStore(db);
  await store.save("test",null,{work:[{id:"read",sourceId:"a",capability:"sold",attempts:0,dueAt:0,status:"pending"}],sources:[{id:"a",capability:"sold",failures:0,blockedUntil:0,disabled:false}]});
  const policy={baseMs:100,maxDelayMs:1000,maxAttempts:3,circuitThreshold:2,cooldownMs:5000};
  assert.equal((await dispatchRead(db,"test","read","read-token",{async read(){return {ok:true,resultJson:"{}"};}},()=>10,100,policy)).status,"completed");
  assert.equal((await store.load("test")).state.work[0].attempts,1);
  console.log("[D1] Import current published commercial capture");
  const {pullCommercial}=require(resolve(compiled,"commercial-ingestion.js"));
  const imported=await pullCommercial(memory,Date.now());
  assert.ok(imported.inserted>0,"published capture contains no usable TCG observations");
  const replay=await pullCommercial(memory,Date.now());
  if(replay.snapshotId===imported.snapshotId){assert.equal(replay.inserted,0);assert.equal(replay.duplicate,imported.inserted);}
  console.log("[D1] Published capture summary",JSON.stringify(imported));
  console.log("D1 local runtime integration passed");
 }catch(error){console.error("[D1] Integration failure:",error);if(error?.cause)console.error("[D1] Underlying cause:",error.cause);throw error;}finally{await mf.dispose();}
})().catch(e=>{console.error(e);process.exitCode=1;});
