import { recover, recordSuccess, type Failure, type SourceHealth, type RetryPolicy, type Attempt } from "./recovery";
export type Work = Attempt & {dueAt:number; status:"pending"|"completed"|"quarantined"};
export type ReadResult = {ok:true; resultJson:string}|{ok:false; failure:Failure; retryAfterMs?:number};
export interface ReadAdapter {
 /** Read-only operation. No purchases, notifications or other external writes. */
 read(job:Readonly<Work>):Promise<ReadResult>;
}
export type Execution = {work:Work; sources:SourceHealth[]; resultJson:string|null; reason:string};
/** The caller must claim the task before invocation and durably save the transition.
 * Attempts here count completed calls; crash-safe attempt accounting requires the durable dispatcher. */
export async function executeRecoveryStep(work:Work,sources:readonly SourceHealth[],adapter:ReadAdapter,now:number,policy:RetryPolicy):Promise<Execution>{
 const unchanged=(reason:string):Execution=>({work:{...work},sources:sources.map(s=>({...s})),resultJson:null,reason});
 if(!Number.isSafeInteger(now)||now<0||!Number.isSafeInteger(work.dueAt)||work.dueAt<0||!Number.isSafeInteger(work.attempts)||work.attempts<0||!Number.isSafeInteger(policy.maxAttempts)||policy.maxAttempts<1)throw new Error("invalid execution state");
 if(work.status!=="pending"||work.dueAt>now)return unchanged("not_due");
 if(work.attempts>=policy.maxAttempts)return {...unchanged("attempt_limit"),work:{...work,status:"quarantined"}};
 const source=sources.find(s=>s.id===work.sourceId&&s.capability===work.capability);
 if(!source)throw new Error("unknown source");
 if(source.disabled||source.blockedUntil>now)return unchanged("source_unavailable");
 const attempt={...work,attempts:work.attempts+1};
 // Transport exceptions are intentionally propagated; unknown outcomes must not be assumed successful.
 const response=await adapter.read(attempt);
 if(response.ok){
  JSON.parse(response.resultJson);
  return {work:{...attempt,status:"completed"},sources:sources.map(s=>s.id===source.id?recordSuccess(s,now):{...s}),resultJson:response.resultJson,reason:"success"};
 }
 const r=recover(sources,attempt,response.failure,now,policy,response.retryAfterMs??0);
 return {work:{...attempt,status:r.action==="quarantine"?"quarantined":"pending",sourceId:r.sourceId??attempt.sourceId,dueAt:r.dueAt??now},sources:r.state,resultJson:null,reason:r.reason};
}
