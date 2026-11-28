import type { Database } from "./d1-store";
import { JobLeases } from "./job-lease";
import { RecoveryStore } from "./recovery-store";
import { executeReservedAttempt, type ReadAdapter } from "./recovery-executor";
import type { RetryPolicy } from "./recovery";

/** Read-only dispatch. Caller supplies a fresh unique token for each invocation.
 * A result is authoritative even if subsequent recovery-state reconciliation conflicts.
 * Unknown transport outcomes consume an attempt and leave the lease to expire.
 */
export async function dispatchRead(db:Database,scope:string,id:string,token:string,
 adapter:ReadAdapter,clock:()=>number,ttl:number,policy:RetryPolicy){
 const leases=new JobLeases(db),store=new RecoveryStore(db);
 const now=clock();
 const prior=await db.prepare("SELECT result_json FROM ecosystem_job_result WHERE scope=? AND job_id=?").bind(scope,id).first<{result_json:string}>();
 if(prior)return {status:"already_completed" as const,resultJson:prior.result_json};
 const snapshot=await store.load(scope);
 const job=snapshot?.state.work.find(w=>w.id===id);
 if(!job||job.status!=="pending"||job.dueAt>now||job.attempts>=policy.maxAttempts)return {status:"not_ready" as const};
 if(!await leases.claim(scope,id,token,now,ttl))return {status:"busy" as const};
 const reserved=await store.reserveAttempt(scope,id,now,policy.maxAttempts);
 if(!reserved)return {status:"not_ready" as const};
 const execution=await executeReservedAttempt(reserved.work,reserved.state.sources,adapter,now,policy);
 const finished=clock();
 if(!Number.isSafeInteger(finished)||finished<now)throw new Error("invalid completion clock");
 const state={work:reserved.state.work.map(w=>w.id===id?execution.work:w),sources:execution.sources};
 if(execution.resultJson!==null){
  if(!await leases.completeWithResult(scope,id,token,finished,execution.resultJson))return {status:"lease_lost" as const};
  const saved=await store.save(scope,reserved.version,state);
  return {status:"completed" as const,resultJson:execution.resultJson,stateReconciled:saved};
 }
 // Failure transition must be fenced by both the recovery version and current lease.
 const r=await db.prepare("UPDATE ecosystem_recovery_state SET version=version+1,state_json=? WHERE scope=? AND version=? AND EXISTS (SELECT 1 FROM ecosystem_job_lease WHERE scope=? AND job_id=? AND token=? AND completed_at IS NULL AND expires_at>?)").bind(JSON.stringify(state),scope,reserved.version,scope,id,token,finished).run();
 if(!r.success||typeof r.meta?.changes!=="number")throw new Error("recovery transition failed");
 if(r.meta.changes!==1)return {status:"transition_conflict" as const};
 const release=await db.prepare("UPDATE ecosystem_job_lease SET expires_at=? WHERE scope=? AND job_id=? AND token=? AND completed_at IS NULL AND expires_at>?").bind(finished,scope,id,token,finished).run();
 if(!release.success)throw new Error("lease release failed");
 return {status:execution.work.status==="quarantined"?"quarantined" as const:"retry_scheduled" as const,dueAt:execution.work.dueAt,sourceId:execution.work.sourceId};
}
