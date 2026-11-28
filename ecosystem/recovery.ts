export type Failure = "transient" | "rate_limited" | "permanent";
export type SourceHealth = { id:string; capability:string; failures:number; blockedUntil:number; disabled:boolean };
export type RetryPolicy = { baseMs:number; maxDelayMs:number; maxAttempts:number; circuitThreshold:number; cooldownMs:number };
export type Attempt = { id:string; capability:string; attempts:number; sourceId:string };
export type Recovery = { state:SourceHealth[]; action:"retry"|"failover"|"defer"|"quarantine"; sourceId:string|null; dueAt:number|null; reason:string };
const integer=(v:number,min=0)=>Number.isSafeInteger(v)&&v>=min;
export function recover(sources:readonly SourceHealth[],job:Attempt,failure:Failure,now:number,p:RetryPolicy,retryAfterMs=0):Recovery{
 if(!integer(now)||!integer(retryAfterMs)||!integer(job.attempts,1)||!job.id.trim()||!job.capability.trim()||!["transient","rate_limited","permanent"].includes(failure)||![p.baseMs,p.maxDelayMs,p.maxAttempts,p.circuitThreshold,p.cooldownMs].every(v=>integer(v,1))||p.baseMs>p.maxDelayMs)throw new Error("invalid recovery policy");
 const ids=new Set<string>();
 for(const s of sources){if(!s.id.trim()||!s.capability.trim()||ids.has(s.id)||!integer(s.failures)||!integer(s.blockedUntil)||typeof s.disabled!=="boolean")throw new Error("invalid source");ids.add(s.id);}
 const source=sources.find(s=>s.id===job.sourceId&&s.capability===job.capability);
 if(!source)throw new Error("unknown or incompatible source");
 const failures=source.failures+1;
 const delay=Math.min(p.maxDelayMs,p.baseMs*2**Math.min(52,job.attempts-1));
 const wait=Math.max(delay,failure==="rate_limited"?retryAfterMs:0);
 const due=now+wait;
 const blockedUntil=Math.max(source.blockedUntil,due,failures>=p.circuitThreshold?now+p.cooldownMs:0);
 if(!integer(failures)||!integer(due)||!integer(blockedUntil))throw new Error("recovery overflow");
 const state=sources.map(s=>s.id===source.id?{...s,failures,blockedUntil,disabled:s.disabled||failure==="permanent"}:{...s});
 if(job.attempts>=p.maxAttempts)return {state,action:"quarantine",sourceId:null,dueAt:null,reason:"attempt_limit"};
 const alternatives=state.filter(s=>s.id!==source.id&&s.capability===job.capability&&!s.disabled).sort((a,b)=>a.blockedUntil-b.blockedUntil||a.failures-b.failures||a.id.localeCompare(b.id));
 const ready=alternatives.find(s=>s.blockedUntil<=now);
 if(ready)return {state,action:"failover",sourceId:ready.id,dueAt:now,reason:"compatible_source_available"};
 const candidates=state.filter(s=>s.capability===job.capability&&!s.disabled).sort((a,b)=>a.blockedUntil-b.blockedUntil||a.failures-b.failures||a.id.localeCompare(b.id));
 const next=candidates[0];
 if(!next)return {state,action:"quarantine",sourceId:null,dueAt:null,reason:"no_compatible_source"};
 return {state,action:next.id===source.id&&failures<p.circuitThreshold?"retry":"defer",sourceId:next.id,dueAt:Math.max(now,next.blockedUntil),reason:"wait_for_source"};
}
export function recordSuccess(source:SourceHealth,now:number):SourceHealth{
 if(!integer(now)||source.disabled||now<source.blockedUntil)throw new Error("source unavailable");
 return {...source,failures:0,blockedUntil:0};
}
