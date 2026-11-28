import {createHash} from "node:crypto";
import {remember,type MemoryStore} from "./memory";
const digest=(s:string)=>createHash("sha256").update(s,"utf8").digest("hex");
const base="https://raw.githubusercontent.com/leseke/Edge-collector/edge/commercial-history/";
type Row={id?:unknown;product_id?:unknown;seller?:unknown;url?:unknown;observed_at?:unknown;status?:unknown;price_kind?:unknown;price?:unknown;currency?:unknown;completed_sale?:unknown;market_language_verified?:unknown;availability?:unknown;source_updated_at?:unknown};
const str=(x:unknown):x is string=>typeof x==="string"&&x.trim().length>0;
export async function ingestCommercial(pointerText:string,reportText:string,store:MemoryStore,now:number){
 if(!Number.isSafeInteger(now)||now<0)throw Error("invalid clock");
 const p=JSON.parse(pointerText),r=JSON.parse(reportText);
 const ref=p.files?.["report.json"];
 if(p.schema!=="edge.public.live_capture.v1"||!/^\d+-\d+$/.test(p.snapshot_id)||ref?.path!==`snapshots/${p.snapshot_id}/report.json`||digest(reportText)!==ref.sha256||r.schema!=="edge.commercial.snapshot.v1"||r.status!==p.status||r.observed_at!==p.observed_at||!Array.isArray(r.observations)||!["OK","PARTIAL","EMPTY","FAILED"].includes(p.status))throw Error("invalid published capture");
 const captured=Date.parse(p.observed_at);
 if(!Number.isFinite(captured)||captured>now)throw Error("invalid capture time");
 const summary={snapshotId:p.snapshot_id,status:p.status,inserted:0,duplicate:0,excluded:0,invalid:0,indicative:0,asking:0,declaredSales:0,subjects:[] as string[]};
 const subjects=new Set<string>();
 for(const row of r.observations as Row[]){
  if(!str(row.product_id)||!/^pokemon_card_[a-zA-Z0-9_.-]+$/.test(row.product_id)){summary.excluded++;continue;}
  if(!str(row.id)||!str(row.seller)||!str(row.url)||!str(row.observed_at)||row.status!=="OK"){summary.invalid++;continue;}
  const at=Date.parse(row.observed_at);
  let url:URL;try{url=new URL(row.url);}catch{summary.invalid++;continue;}
  if(!Number.isFinite(at)||at<0||at>now||url.protocol!=="https:"||url.username||url.password){summary.invalid++;continue;}
  const kind=row.price_kind==="AGGREGATED_INDICATIVE_LOW"&&row.completed_sale!==true?"indicative":row.price_kind==="ASKING_PRICE"&&row.completed_sale!==true?"asking":row.price_kind==="SOLD_PRICE"&&row.completed_sale===true?"declared_sale":null;
  const price=typeof row.price==="string"&&/^\d+(?:\.\d{1,2})?$/.test(row.price)?Math.round(Number(row.price)*100):null;
  if(!kind||price===null||!Number.isSafeInteger(price)||price<=0||row.currency!=="EUR"){summary.invalid++;continue;}
  const id=JSON.stringify(["commercial-capture",p.snapshot_id,row.id]);
  const old=await store.get(id);
  const entry={id,subject:row.product_id,kind:"observation" as const,recordedAt:old?.recordedAt??now,occurredAt:at,sourceUrl:url.href,evidenceIds:[],statement:JSON.stringify({schema:"edge.ecosystem.commercial.v1",snapshotId:p.snapshot_id,reportSha256:ref.sha256,source:row.seller,priceMinor:price,currency:"EUR",priceKind:kind,marketLanguage:"UNKNOWN",marketLanguageVerified:row.market_language_verified===true,availability:str(row.availability)?row.availability:"UNKNOWN",sourceUpdatedAt:str(row.source_updated_at)?row.source_updated_at:null,independentlyVerified:false})};
  const result=await remember(store,entry,now);summary[result]++;subjects.add(row.product_id);
  if(kind==="indicative")summary.indicative++;else if(kind==="asking")summary.asking++;else summary.declaredSales++;
 }
 summary.subjects=[...subjects].sort();
 return summary;
}
export async function pullCommercial(store:MemoryStore,now:number,fetcher:typeof fetch=fetch){
 async function read(path:string){const response=await fetcher(base+path,{redirect:"error",cache:"no-store",signal:AbortSignal.timeout(10000)});if(!response.ok)throw Error("capture unavailable: "+response.status);const value=await response.text();if(Buffer.byteLength(value)>5_000_000)throw Error("capture too large");return value;}
 const pointer=await read("latest.json");const p=JSON.parse(pointer);
 if(!/^\d+-\d+$/.test(p.snapshot_id))throw Error("invalid snapshot ID");
 return ingestCommercial(pointer,await read(`snapshots/${p.snapshot_id}/report.json`),store,now);
}

/** Replay immutable publisher commits, using the original pointer and report.
 * The cursor is supplied by the caller; a bounded page never silently skips failures.
 */
export async function pullCommercialHistory(store:MemoryStore,now:number,commits:readonly string[],fetcher:typeof fetch=fetch){
 if(commits.length>20||commits.some(sha=>!/^[a-f0-9]{40}$/.test(sha))||new Set(commits).size!==commits.length)throw Error("invalid history page");
 const results:Awaited<ReturnType<typeof ingestCommercial>>[]=[];
 const failures:{commit:string;reason:string}[]=[];
 for(const commit of commits){
  try{
   const root="https://raw.githubusercontent.com/leseke/Edge-collector/"+commit+"/";
   const read=async(path:string)=>{const response=await fetcher(root+path,{redirect:"error",cache:"no-store",signal:AbortSignal.timeout(10000)});if(!response.ok)throw Error("history unavailable: "+response.status);const value=await response.text();if(Buffer.byteLength(value)>5_000_000)throw Error("history too large");return value;};
   const pointer=await read("latest.json"),p=JSON.parse(pointer);
   if(!/^\d+-\d+$/.test(p.snapshot_id))throw Error("invalid snapshot ID");
   results.push(await ingestCommercial(pointer,await read(`snapshots/${p.snapshot_id}/report.json`),store,now));
  }catch(error){failures.push({commit,reason:error instanceof Error?error.message:"unknown failure"});}
 }
 return {results,failures,subjects:[...new Set(results.flatMap(r=>r.subjects))].sort()};
}
export async function discoverCommercialHistory(page:number,fetcher:typeof fetch=fetch):Promise<string[]>{
 if(!Number.isSafeInteger(page)||page<1||page>1000)throw Error("invalid history page");
 const url="https://api.github.com/repos/leseke/Edge-collector/commits?sha=edge%2Fcommercial-history&path=latest.json&per_page=10&page="+page;
 const response=await fetcher(url,{redirect:"error",headers:{Accept:"application/vnd.github+json"},signal:AbortSignal.timeout(10000)});
 if(!response.ok)throw Error("history index unavailable: "+response.status);
 const rows:unknown=await response.json();
 if(!Array.isArray(rows)||rows.length>10||rows.some(r=>!r||typeof r.sha!=="string"||!/^[a-f0-9]{40}$/.test(r.sha)))throw Error("invalid history index");
 return [...new Set(rows.map(r=>r.sha as string))];
}
