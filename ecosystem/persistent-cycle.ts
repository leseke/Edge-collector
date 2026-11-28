import { cycle, type CycleInput, type CyclePolicy, type CycleState } from "./homeostasis";
import { D1Memory, D1Checkpoints, type Database } from "./d1-store";
/** Observation writes are idempotent; checkpoint conflicts must never dispatch work.
 * Dispatchers must separately claim jobs atomically and acknowledge durable results.
 */
export async function persistentCycle(db:Database,id:string,initial:CycleState,input:CycleInput,now:number,policy:CyclePolicy){
 const checkpoints=new D1Checkpoints(db);
 const prior=await checkpoints.load(id);
 const result=await cycle(prior?.state??initial,input,new D1Memory(db),now,policy);
 const committed=await checkpoints.save(id,prior?.version??null,result.state,now);
 if(!committed)return {committed:false as const,reason:"checkpoint_conflict" as const};
 return {committed:true as const,version:prior?prior.version+1:0,result};
}
