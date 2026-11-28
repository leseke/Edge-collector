import type { Database } from "./d1-store";
import type { Work } from "./recovery-executor";
import type { SourceHealth } from "./recovery";
export type RecoveryState={work:Work[];sources:SourceHealth[]};
export class RecoveryStore {
 constructor(private readonly db:Database){}
 async load(scope:string):Promise<{version:number;state:RecoveryState}|null>{
  const r=await this.db.prepare("SELECT version,state_json FROM ecosystem_recovery_state WHERE scope=?").bind(scope).first<{version:number;state_json:string}>();
  return r?{version:r.version,state:JSON.parse(r.state_json) as RecoveryState}:null;
 }
 async save(scope:string,version:number|null,state:RecoveryState){
  if(!scope.trim()||version!==null&&(!Number.isSafeInteger(version)||version<0||version>=Number.MAX_SAFE_INTEGER))throw new Error("invalid recovery version");
  const json=JSON.stringify(state);
  const q=version===null?this.db.prepare("INSERT INTO ecosystem_recovery_state(scope,version,state_json) VALUES(?,0,?) ON CONFLICT(scope) DO NOTHING").bind(scope,json):this.db.prepare("UPDATE ecosystem_recovery_state SET version=version+1,state_json=? WHERE scope=? AND version=?").bind(json,scope,version);
  const r=await q.run();if(!r.success||typeof r.meta?.changes!=="number")throw new Error("recovery write failed");return r.meta.changes===1;
 }
 /** Reserve an attempt durably. Caller must also hold a unique job lease. */
 async reserveAttempt(scope:string,id:string,now:number,maxAttempts:number){
  if(!Number.isSafeInteger(now)||now<0||!Number.isSafeInteger(maxAttempts)||maxAttempts<1)throw new Error("invalid attempt policy");
  const current=await this.load(scope);if(!current)return null;
  const work=current.state.work.find(w=>w.id===id);
  if(!work||work.status!=="pending"||work.dueAt>now||work.attempts>=maxAttempts)return null;
  const source=current.state.sources.find(s=>s.id===work.sourceId&&s.capability===work.capability);
  if(!source||source.disabled||source.blockedUntil>now)return null;
  const next={...work,attempts:work.attempts+1};
  const state={...current.state,work:current.state.work.map(w=>w.id===id?next:w)};
  if(!await this.save(scope,current.version,state))return null;
  return {version:current.version+1,state,work:next};
 }
}
