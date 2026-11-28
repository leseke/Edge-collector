const assert=require("node:assert/strict");
const {randomUUID}=require("node:crypto");
const {readFileSync}=require("node:fs");
const {resolve}=require("node:path");
const {JobLeases}=require(resolve(process.env.EDGE_COMPILED,"job-lease.js"));
const {executeExternal}=require(resolve(process.env.EDGE_COMPILED,"external-operation.js"));
const {CLOUDFLARE_ACCOUNT_ID:account,EDGE_STAGING_D1_ID:database,CLOUDFLARE_API_TOKEN:token}=process.env;
assert.match(account||"",/^[a-f0-9]{32}$/i);
assert.match(database||"",/^[a-f0-9-]{36}$/i);
assert.ok(token,"missing staging credential");
const url="https://api.cloudflare.com/client/v4/accounts/"+account+"/d1/database/"+database;
async function api(path,body){
 const res=await fetch(url+path,{method:body?"POST":"GET",headers:{Authorization:"Bearer "+token,"Content-Type":"application/json"},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(30000),redirect:"error"});
 const data=await res.json();
 if(!res.ok||!data.success)throw new Error("Cloudflare API failed: HTTP "+res.status+" codes "+(data.errors||[]).map(e=>e.code).join(","));
 return data.result;
}
async function query(sql,params=[]){
 const rows=await api("/query",{sql,params});
 assert.equal(rows.length,1);
 assert.equal(rows[0].success,true);
 return rows[0];
}
class Statement{
 constructor(sql,params=[]){this.sql=sql;this.params=params;}
 bind(...params){return new Statement(this.sql,params);}
 run(){return query(this.sql,this.params);}
 all(){return this.run();}
 async first(){return (await this.run()).results[0]??null;}
}
const db={prepare:sql=>new Statement(sql),batch(){throw new Error("REST smoke does not emulate atomic Workers batches");}};
(async()=>{
 const info=await api("");
 assert.equal(info.name,"edge-ecosystem-staging","refusing non-staging database");
 assert.equal(info.uuid,database,"database identity mismatch");
 console.log("Verified staging database identity");
 for(const name of ["memory","checkpoint","job-lease","job-result","recovery-state","dispatch-lock","external-operation"]){
  const sql=readFileSync("ecosystem/"+name+".sql","utf8").replace(/^--.*$/gm,"");
  const statements=sql.match(/CREATE TRIGGER[\s\S]*?END;|CREATE (?:TABLE|INDEX)[\s\S]*?;/gi)||[];
  assert.ok(statements.length);
  for(const statement of statements)await query(statement);
 }
 const scope="ci-"+randomUUID(),leases=new JobLeases(db);
 assert.equal(await leases.claim(scope,"j","a",10,20),true);
 assert.equal(await leases.claim(scope,"j","b",11,20),false);
 assert.equal(await leases.claim(scope,"j","b",30,20),true);
 assert.equal(await leases.completeWithResult(scope,"j","a",31,"{}"),false);
 assert.equal(await leases.completeWithResult(scope,"j","b",31,"{}"),true);
 assert.equal(await leases.claim(scope,"j","c",100,20),false);
 const row=await db.prepare("SELECT result_json FROM ecosystem_job_result WHERE scope=? AND job_id=?").bind(scope,"j").first();
 assert.equal(row.result_json,"{}");
 let calls=0;const q={scope,id:"external",fingerprint:"fixture",token:"a"};
 const invoke=async()=>{calls++;return "{}";};
 assert.equal((await executeExternal(db,q,()=>10,invoke)).status,"completed");
 assert.equal((await executeExternal(db,{...q,token:"b"},()=>11,invoke)).status,"cached");
 assert.equal(calls,1);
 console.log("Remote staging D1 REST smoke passed; synthetic scope "+scope);
})().catch(e=>{console.error(e.message);process.exitCode=1;});
