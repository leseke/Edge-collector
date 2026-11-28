export type EntryKind = "observation" | "verification" | "hypothesis" | "outcome" | "decision";
export type MemoryEntry = { id:string; subject:string; kind:EntryKind; recordedAt:number; occurredAt:number; statement:string; evidenceIds:readonly string[]; sourceUrl?:string; hypothesisId?:string; outcome?: "supported"|"contradicted"|"inconclusive" };
/** Storage must atomically enforce unique IDs, immutable records and reference integrity. */
export interface MemoryStore {
  append(entry:MemoryEntry):Promise<"inserted"|"duplicate">;
  get(id:string):Promise<MemoryEntry|null>;
  timeline(subject:string, before:number, limit:number):Promise<readonly MemoryEntry[]>;
}
const kinds:readonly EntryKind[]=["observation","verification","hypothesis","outcome","decision"];
export async function remember(store:MemoryStore,entry:MemoryEntry,now:number) {
 if(!Number.isSafeInteger(now)||!Number.isSafeInteger(entry.recordedAt)||!Number.isSafeInteger(entry.occurredAt)||entry.occurredAt<0||entry.occurredAt>entry.recordedAt||entry.recordedAt>now||!entry.id.trim()||!entry.subject.trim()||!entry.statement.trim()||!kinds.includes(entry.kind)) throw new Error("invalid memory");
 if(new Set(entry.evidenceIds).size!==entry.evidenceIds.length||entry.evidenceIds.includes(entry.id)) throw new Error("invalid evidence links");
 if(entry.kind==="observation"){if(!entry.sourceUrl||new URL(entry.sourceUrl).protocol!=="https:") throw new Error("observation requires source");}
 if(entry.kind!=="observation"&&entry.evidenceIds.length===0) throw new Error("evidence required");
 for(const id of entry.evidenceIds){const evidence=await store.get(id);if(!evidence||evidence.recordedAt>entry.recordedAt) throw new Error("unknown or future evidence");}
 if(entry.kind==="outcome"){
  const h=entry.hypothesisId?await store.get(entry.hypothesisId):null;
  if(!h||h.kind!=="hypothesis"||h.subject!==entry.subject||h.recordedAt>entry.occurredAt||!entry.outcome||!["supported","contradicted","inconclusive"].includes(entry.outcome)) throw new Error("invalid outcome");
 }else if(entry.outcome!==undefined||entry.hypothesisId!==undefined) throw new Error("outcome fields reserved");
 return store.append(entry);
}
export async function recall(store:MemoryStore,subject:string,asOf:number,limit=100){
 if(!subject.trim()||!Number.isSafeInteger(asOf)||asOf<0||!Number.isSafeInteger(limit)||limit<1||limit>1000) throw new Error("invalid recall");
 const records=await store.timeline(subject,asOf,limit);
 return records.filter(e=>e.subject===subject&&e.recordedAt<=asOf).sort((a,b)=>b.recordedAt-a.recordedAt||a.id.localeCompare(b.id)).slice(0,limit);
}
