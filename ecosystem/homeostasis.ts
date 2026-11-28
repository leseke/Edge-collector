import { tick, type NervousState, type Signal } from "./nervous-system";
import { inspect, type Observation, type Reference } from "./immune-system";
import { remember, type MemoryStore } from "./memory";
import { anticipate, type MarketSignal } from "./anticipation";
import { adapt, type Channel, type Feedback, type Policy } from "./adaptation";
import type { Job } from "./regulator";
export type CycleState = { nervous:NervousState; outstanding:Job[] };
export type CycleInput = { observations:readonly Observation[]; previous:readonly Observation[]; references:readonly Reference[]; signals:readonly Signal[]; marketSignals:readonly MarketSignal[]; channels:readonly Channel[]; feedback:readonly Feedback[] };
export type CyclePolicy = { costs:Record<Job["kind"],number>; ttlMs:number; marketWindowMs:number; adaptation:Policy };
/** Caller must serialize cycles and persist returned state before dispatching outstanding jobs.
 * External verification and source identity resolution are adapter responsibilities. */
export async function cycle(state:CycleState,input:CycleInput,store:MemoryStore,now:number,p:CyclePolicy){
 if(!Number.isSafeInteger(now)||now<0||!Number.isSafeInteger(p.ttlMs)||p.ttlMs<=0||!Number.isSafeInteger(now+p.ttlMs))throw new Error("invalid cycle clock");
 const signals=[...input.signals];
 const previous=[...input.previous];
 const verdicts=[];
 for(const o of input.observations){
  const verdict=inspect(o,previous,input.references,now,p.ttlMs);
  verdicts.push({id:o.id,...verdict});
  if(verdict.status==="duplicate")continue;
  if(verdict.status==="rejected"){if(verdict.signal)signals.push(verdict.signal);continue;}
  const id=JSON.stringify(["observation",o.id]);
  const existing=await store.get(id);
  const entry={id,subject:o.subject,kind:"observation" as const,recordedAt:existing?.recordedAt??now,occurredAt:o.observedAt,statement:JSON.stringify(o),sourceUrl:o.url,evidenceIds:[]};
  await remember(store,entry,now);
  previous.push(o);
  signals.push({id:JSON.stringify([id,"observed"]),kind:"listing.observed",subject:o.subject,observedAt:entry.recordedAt,expiresAt:entry.recordedAt+p.ttlMs});
 }
 const evidenced:MarketSignal[]=[];
 for(const s of input.marketSignals){
  const e=await store.get(s.evidenceId);
  if(!e||e.subject!==s.subject||e.recordedAt>s.recordedAt||e.recordedAt>now||!["observation","verification"].includes(e.kind))continue;
  evidenced.push({...s,verified:s.verified&&e.kind==="verification"});
 }
 const feedback:Feedback[]=[];
 for(const f of input.feedback){const e=await store.get(f.evidenceId);if(e&&e.recordedAt<=f.recordedAt&&e.recordedAt<=now&&(e.kind==="outcome"||e.kind==="verification"))feedback.push(f);}
 const leads=anticipate(evidenced,now,p.marketWindowMs);
 const recommendations=adapt(input.channels,feedback,now,p.adaptation);
 const result=tick(state.nervous,signals,now,p.costs);
 const outstanding=new Map(state.outstanding.map(j=>[j.id,j]));
 for(const j of result.admitted)if(!outstanding.has(j.id))outstanding.set(j.id,j);
 return {state:{nervous:result.state,outstanding:[...outstanding.values()]},verdicts,leads,recommendations,processed:result.processed,rejected:result.rejected};
}
export function acknowledge(state:CycleState,id:string):CycleState{
 return {...state,outstanding:state.outstanding.filter(j=>j.id!==id)};
}
