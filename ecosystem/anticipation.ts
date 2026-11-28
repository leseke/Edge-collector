export type SignalFamily = "demand"|"supply"|"catalyst"|"historical_analogue"|"risk";
export type MarketSignal = {id:string; subject:string; family:SignalFamily; sourceGroup:string; eventKey:string; evidenceId:string; recordedAt:number; direction:"positive"|"negative"; strength:number; verified:boolean};
export type EarlyLead = {subject:string; status:"WATCH"|"PRESHOT_REVIEW"; score:number; evidenceIds:string[]; risks:string[]; families:SignalFamily[]; sourceCount:number; verifiedCount:number; asOf:number; executionAllowed:false};
const families:SignalFamily[]=["demand","supply","catalyst","historical_analogue","risk"];
/** Discovery score is a heuristic, never a probability or a trade authorization.
 * sourceGroup/eventKey must be resolved upstream to shared origin, not publisher aliases. */
export function anticipate(signals:readonly MarketSignal[],now:number,windowMs:number):EarlyLead[]{
 if(!Number.isSafeInteger(now)||now<0||!Number.isSafeInteger(windowMs)||windowMs<=0)throw new Error("invalid horizon");
 const unique=new Map<string,MarketSignal>();
 for(const s of signals){
  if(![s.id,s.subject,s.sourceGroup,s.eventKey,s.evidenceId].every(v=>typeof v==="string"&&v.trim())||!families.includes(s.family)||!["positive","negative"].includes(s.direction)||typeof s.verified!=="boolean"||!Number.isFinite(s.strength)||s.strength<0||s.strength>1||!Number.isSafeInteger(s.recordedAt)||s.recordedAt<0||s.recordedAt>now||(s.family==="risk"&&s.direction!=="negative"))throw new Error("invalid signal");
  if(s.recordedAt<now-windowMs)continue;
  const key=JSON.stringify([s.subject,s.eventKey]);
  const old=unique.get(key);
  if(old&&(old.direction!==s.direction||old.family!==s.family))throw new Error("conflicting event");
  if(!old||Number(s.verified)>Number(old.verified)||(s.verified===old.verified&&(s.strength>old.strength||(s.strength===old.strength&&s.id<old.id))))unique.set(key,s);
 }
 const bySubject=new Map<string,MarketSignal[]>();
 for(const s of unique.values()){const list=bySubject.get(s.subject)??[];list.push(s);bySubject.set(s.subject,list);}
 const leads:EarlyLead[]=[];
 for(const [subject,items] of bySubject){
  const positive=items.filter(s=>s.direction==="positive");
  if(!positive.length)continue;
  const negative=items.filter(s=>s.direction==="negative");
  const groups=new Set(positive.map(s=>s.sourceGroup));
  const fs=[...new Set(positive.map(s=>s.family))].sort();
  const maxByFamily=new Map<SignalFamily,number>();
  for(const s of positive)maxByFamily.set(s.family,Math.max(maxByFamily.get(s.family)??0,s.strength*(s.verified?1:0.5)));
  const positiveScore=[...maxByFamily.values()].reduce((a,b)=>a+b,0)*25;
  const penalty=Math.min(50,negative.reduce((a,s)=>a+s.strength*(s.verified?1:0.5)*15,0));
  const score=Math.round(Math.max(0,Math.min(100,positiveScore-penalty)));
  leads.push({subject,status:groups.size>=2&&fs.length>=2&&score>=35?"PRESHOT_REVIEW":"WATCH",score,evidenceIds:[...new Set(items.map(s=>s.evidenceId))].sort(),risks:negative.map(s=>s.evidenceId).sort(),families:fs,sourceCount:groups.size,verifiedCount:items.filter(s=>s.verified).length,asOf:now,executionAllowed:false});
 }
 return leads.sort((a,b)=>b.score-a.score||a.subject.localeCompare(b.subject));
}
