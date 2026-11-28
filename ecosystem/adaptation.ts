export type Feedback = { id:string; channel:string; recordedAt:number; outcome:"useful"|"not_useful"|"inconclusive"|"source_error"; evidenceId:string };
export type Channel = { id:string; lastProbeAt:number; baselineIntervalMs:number };
export type Policy = { windowMs:number; minSamples:number; minIntervalMs:number; maxIntervalMs:number };
export type Recommendation = { channel:string; intervalMs:number; nextProbeAt:number; priority:number; samples:number; reason:string };
const positiveInt=(n:number)=>Number.isSafeInteger(n)&&n>0;
export function adapt(channels:readonly Channel[], feedback:readonly Feedback[], now:number, p:Policy):Recommendation[] {
 if(!Number.isSafeInteger(now)||now<0||![p.windowMs,p.minSamples,p.minIntervalMs,p.maxIntervalMs].every(positiveInt)||p.minIntervalMs>p.maxIntervalMs) throw new Error("invalid adaptation policy");
 const ids=new Set<string>();
 for(const c of channels){if(!c.id.trim()||ids.has(c.id)||!positiveInt(c.baselineIntervalMs)||!Number.isSafeInteger(c.lastProbeAt)||c.lastProbeAt<0||c.lastProbeAt>now)throw new Error("invalid channel");ids.add(c.id);}
 const unique=new Map<string,Feedback>();
 for(const f of feedback){
  if(!ids.has(f.channel)||!f.id.trim()||!f.evidenceId.trim()||!Number.isSafeInteger(f.recordedAt)||f.recordedAt<0||f.recordedAt>now||!["useful","not_useful","inconclusive","source_error"].includes(f.outcome))throw new Error("invalid feedback");
  const key=JSON.stringify([f.channel,f.evidenceId]);
  const old=unique.get(key);
  if(old && (old.outcome!==f.outcome||old.recordedAt!==f.recordedAt))throw new Error("conflicting feedback");
  unique.set(key,f);
 }
 return channels.map(c=>{
  const recent=[...unique.values()].filter(f=>f.channel===c.id&&f.recordedAt>=now-p.windowMs);
  const useful=recent.filter(f=>f.outcome==="useful").length;
  const notUseful=recent.filter(f=>f.outcome==="not_useful").length;
  const samples=useful+notUseful;
  const rate=(useful+2)/(samples+4);
  const mature=samples>=p.minSamples;
  const multiplier=mature?1.5-rate:1;
  const intervalMs=Math.min(p.maxIntervalMs,Math.max(p.minIntervalMs,Math.round(c.baselineIntervalMs*multiplier)));
  const nextProbeAt=c.lastProbeAt+intervalMs;
  if(!Number.isSafeInteger(nextProbeAt))throw new Error("probe time overflow");
  return {channel:c.id,intervalMs,nextProbeAt,priority:mature?Math.round(25+50*rate):50,samples,reason:mature?"bounded_measured_yield":"insufficient_conclusive_evidence"};
 });
}
