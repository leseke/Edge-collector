import type { MemoryEntry, MemoryStore } from "./memory";
import type { CycleState } from "./homeostasis";
type Value = string | number | null;
type Result<T> = {success:boolean; results?:T[]; meta?:{changes?:number}};
export interface Statement {
 bind(...values:Value[]):Statement;
 first<T>():Promise<T|null>;
 all<T>():Promise<Result<T>>;
 run():Promise<Result<unknown>>;
}
export interface Database {
 prepare(sql:string):Statement;
 batch(statements:Statement[]):Promise<Result<unknown>[]>;
}
type Row = {id:string;subject:string;kind:MemoryEntry["kind"];recorded_at:number;occurred_at:number;statement:string;source_url:string|null;hypothesis_id:string|null;outcome:MemoryEntry["outcome"]|null};
const same=(a:MemoryEntry,b:MemoryEntry)=>a.id===b.id&&a.subject===b.subject&&a.kind===b.kind&&a.recordedAt===b.recordedAt&&a.occurredAt===b.occurredAt&&a.statement===b.statement&&a.sourceUrl===b.sourceUrl&&a.hypothesisId===b.hypothesisId&&a.outcome===b.outcome&&JSON.stringify([...a.evidenceIds].sort())===JSON.stringify([...b.evidenceIds].sort());
export class D1Memory implements MemoryStore {
 constructor(private readonly db:Database){}
 private async decode(r:Row):Promise<MemoryEntry>{
  const links=await this.db.prepare("SELECT evidence_id FROM ecosystem_memory_evidence WHERE entry_id=? ORDER BY evidence_id").bind(r.id).all<{evidence_id:string}>();
  if(!links.success)throw new Error("memory read failed");
  return {id:r.id,subject:r.subject,kind:r.kind,recordedAt:r.recorded_at,occurredAt:r.occurred_at,statement:r.statement,sourceUrl:r.source_url??undefined,hypothesisId:r.hypothesis_id??undefined,outcome:r.outcome??undefined,evidenceIds:(links.results??[]).map(x=>x.evidence_id)};
 }
 async get(id:string){const r=await this.db.prepare("SELECT * FROM ecosystem_memory WHERE id=?").bind(id).first<Row>();return r?this.decode(r):null;}
 async append(e:MemoryEntry):Promise<"inserted"|"duplicate">{
  const existing=await this.get(e.id);
  if(existing){if(!same(existing,e))throw new Error("memory ID conflict");return "duplicate";}
  try{
   const statements=[this.db.prepare("INSERT INTO ecosystem_memory(id,subject,kind,recorded_at,occurred_at,statement,source_url,hypothesis_id,outcome) VALUES(?,?,?,?,?,?,?,?,?)").bind(e.id,e.subject,e.kind,e.recordedAt,e.occurredAt,e.statement,e.sourceUrl??null,e.hypothesisId??null,e.outcome??null),
   ...e.evidenceIds.map(id=>this.db.prepare("INSERT INTO ecosystem_memory_evidence(entry_id,evidence_id) VALUES(?,?)").bind(e.id,id))];
   const results=await this.db.batch(statements);
   if(results.length!==statements.length||results.some(r=>!r.success))throw new Error("memory batch failed");
   return "inserted";
  }catch(error){const winner=await this.get(e.id);if(winner&&same(winner,e))return "duplicate";throw error;}
 }
 async timeline(subject:string,before:number,limit:number){
  const rows=await this.db.prepare("SELECT * FROM ecosystem_memory WHERE subject=? AND recorded_at<=? ORDER BY recorded_at DESC,id LIMIT ?").bind(subject,before,limit).all<Row>();
  if(!rows.success)throw new Error("timeline read failed");
  return Promise.all((rows.results??[]).map(r=>this.decode(r)));
 }
}
export type Checkpoint={version:number;state:CycleState};
export class D1Checkpoints {
 constructor(private readonly db:Database){}
 async load(id:string):Promise<Checkpoint|null>{
  const row=await this.db.prepare("SELECT version,state_json FROM ecosystem_checkpoint WHERE id=?").bind(id).first<{version:number;state_json:string}>();
  return row?{version:row.version,state:JSON.parse(row.state_json) as CycleState}:null;
 }
 async save(id:string,expectedVersion:number|null,state:CycleState,now:number):Promise<boolean>{
  if(!id.trim()||!Number.isSafeInteger(now)||now<0||expectedVersion!==null&&(!Number.isSafeInteger(expectedVersion)||expectedVersion<0||expectedVersion>=Number.MAX_SAFE_INTEGER))throw new Error("invalid checkpoint");
  const json=JSON.stringify(state);
  const stmt=expectedVersion===null?this.db.prepare("INSERT INTO ecosystem_checkpoint(id,version,state_json,updated_at) VALUES(?,0,?,?) ON CONFLICT(id) DO NOTHING").bind(id,json,now):this.db.prepare("UPDATE ecosystem_checkpoint SET version=version+1,state_json=?,updated_at=? WHERE id=? AND version=? AND updated_at<=?").bind(json,now,id,expectedVersion,now);
  const r=await stmt.run();
  if(!r.success||typeof r.meta?.changes!=="number")throw new Error("checkpoint write failed");
  return r.meta.changes===1;
 }
}
