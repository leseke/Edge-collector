import {recall,type MemoryEntry,type MemoryStore} from "./memory";
type Point={entry:MemoryEntry;source:string;priceMinor:number;snapshotId:string;updated:number};
function point(e:MemoryEntry):Point|null{
 if(e.kind!=="observation"||!e.sourceUrl)return null;
 try{
 const d=JSON.parse(e.statement);
 if(d.schema!=="edge.ecosystem.commercial.v1"||d.priceKind!=="indicative"||d.currency!=="EUR"||d.marketLanguage!=="UNKNOWN"||typeof d.marketLanguageVerified!=="boolean"||!Number.isSafeInteger(d.priceMinor)||d.priceMinor<=0||typeof d.source!=="string"||!d.source||typeof d.snapshotId!=="string")return null;
 // This first comparison is restricted to the same aggregate feed, not individual cards by language.
 if(new URL(e.sourceUrl).hostname!=="api.tcgdex.net"||d.marketLanguageVerified)return null;
 const updated=Date.parse(d.sourceUpdatedAt);
 if(!Number.isFinite(updated)||updated>e.occurredAt)return null;
 return {entry:e,source:d.source,priceMinor:d.priceMinor,snapshotId:d.snapshotId,updated};
 }catch{return null;}
}
export type PriceVariation={subject:string;kind:"indicative_price_change";previousMinor:number;currentMinor:number;changeMinor:number;changePercent:number;currency:"EUR";previousEvidenceId:string;currentEvidenceId:string;source:string;sourceUrl:string;previousUpdatedAt:number;currentUpdatedAt:number;independentlyVerified:false;executionAllowed:false};
export async function commercialVariations(store:MemoryStore,subject:string,now:number):Promise<PriceVariation[]>{
 const points=(await recall(store,subject,now,1000)).map(point).filter((p):p is Point=>p!==null);
 const groups=new Map<string,Point[]>();
 for(const p of points){const key=JSON.stringify([p.source,p.entry.sourceUrl]);const group=groups.get(key)??[];group.push(p);groups.set(key,group);}
 const result:PriceVariation[]=[];
 for(const group of groups.values()){
  const byTime=new Map<number,Point[]>();
  for(const p of group){const rows=byTime.get(p.updated)??[];rows.push(p);byTime.set(p.updated,rows);}
  const times=[...byTime.keys()].sort((a,b)=>b-a);
  if(times.length<2)continue;
  const latest=byTime.get(times[0])!,prior=byTime.get(times[1])!;
  if(new Set(latest.map(p=>p.priceMinor)).size!==1||new Set(prior.map(p=>p.priceMinor)).size!==1)continue;
  const a=prior.sort((x,y)=>x.entry.occurredAt-y.entry.occurredAt||x.entry.id.localeCompare(y.entry.id))[0];
  const b=latest.sort((x,y)=>x.entry.occurredAt-y.entry.occurredAt||x.entry.id.localeCompare(y.entry.id))[0];
  if(a.snapshotId===b.snapshotId||a.entry.occurredAt>=b.entry.occurredAt||a.priceMinor===b.priceMinor)continue;
  result.push({subject,kind:"indicative_price_change",previousMinor:a.priceMinor,currentMinor:b.priceMinor,changeMinor:b.priceMinor-a.priceMinor,changePercent:(b.priceMinor/a.priceMinor-1)*100,currency:"EUR",previousEvidenceId:a.entry.id,currentEvidenceId:b.entry.id,source:b.source,sourceUrl:b.entry.sourceUrl!,previousUpdatedAt:a.updated,currentUpdatedAt:b.updated,independentlyVerified:false,executionAllowed:false});
 }
 return result;
}
