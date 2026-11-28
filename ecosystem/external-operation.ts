import type { Database } from "./d1-store";
export type ExternalRequest={scope:string;id:string;fingerprint:string;token:string};
export async function executeExternal(db:Database,q:ExternalRequest,clock:()=>number,invoke:()=>Promise<string>){
 const now=clock();
 if(![q.scope,q.id,q.fingerprint,q.token].every(s=>typeof s==="string"&&s.trim())||!Number.isSafeInteger(now)||now<0)throw new Error("invalid external operation");
 const claim=await db.prepare("INSERT INTO ecosystem_external_operation(scope,operation_id,fingerprint,token,started_at) VALUES(?,?,?,?,?) ON CONFLICT(scope,operation_id) DO NOTHING").bind(q.scope,q.id,q.fingerprint,q.token,now).run();
 if(!claim.success||typeof claim.meta?.changes!=="number")throw new Error("external claim failed");
 if(claim.meta.changes!==1){
  const row=await db.prepare("SELECT fingerprint,result_json FROM ecosystem_external_operation WHERE scope=? AND operation_id=?").bind(q.scope,q.id).first<{fingerprint:string;result_json:string|null}>();
  if(!row||row.fingerprint!==q.fingerprint)throw new Error("external operation identity conflict");
  return row.result_json===null?{status:"unresolved" as const}:{status:"cached" as const,resultJson:row.result_json};
 }
 // Any exception leaves a durable unresolved record. Never automatically replay.
 const resultJson=await invoke();
 JSON.parse(resultJson);
 const finished=clock();
 if(!Number.isSafeInteger(finished)||finished<now)throw new Error("invalid completion time");
 const saved=await db.prepare("UPDATE ecosystem_external_operation SET completed_at=?,result_json=? WHERE scope=? AND operation_id=? AND token=? AND completed_at IS NULL").bind(finished,resultJson,q.scope,q.id,q.token).run();
 if(!saved.success||saved.meta?.changes!==1)throw new Error("external result persistence failed");
 return {status:"completed" as const,resultJson};
}
