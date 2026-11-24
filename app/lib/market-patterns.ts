import {median} from "./edge-learning";
type Db={prepare(sql:string):{bind(...args:string[]):{all<T>():Promise<{results:T[]}>}}};
export type PatternSale={lot_id:string;variant_key:string;sold_day:string;price_cents:number;collected_at:string};
export const patternQuery=`
SELECT lot_id,variant_key,sold_day,price_cents,collected_at FROM paid_market_sales
WHERE sold_day>=? AND sold_day<? AND collected_at<=?
AND lot_id LIKE 'gcc-%' AND source_url='https://gradedcardcenter.com/item/'||substr(lot_id,5)
ORDER BY sold_day DESC,lot_id LIMIT 5001`;
export function recognizePatterns(rows:PatternSale[],asOf:string){
 const boundary=Date.parse(asOf.slice(0,10)+"T00:00:00Z");
 const groups=new Map<string,{prior:PatternSale[];recent:PatternSale[]}>();
 const seen=new Set<string>();
 for(const s of rows){
  const age=(boundary-Date.parse(s.sold_day+"T00:00:00Z"))/86400000;
  if(!s.variant_key||seen.has(s.lot_id)||!(age>=1&&age<=28)||s.collected_at>asOf||!Number.isSafeInteger(s.price_cents)||s.price_cents<=0)continue;
  seen.add(s.lot_id);
  const group=groups.get(s.variant_key)??{prior:[],recent:[]};
  (age<=14?group.recent:group.prior).push(s);groups.set(s.variant_key,group);
 }
 return [...groups].flatMap(([variant,group])=>{
  if(group.prior.length<3||group.recent.length<5||group.recent.length<group.prior.length*1.5)return [];
  const before=median(group.prior.map(s=>s.price_cents))!,after=median(group.recent.map(s=>s.price_cents))!;
  const change=100*(after-before)/before;
  if(Math.abs(change)>5)return [];
  return [{variant,priorCount:group.prior.length,recentCount:group.recent.length,before,after,change,evidence:group.recent.slice(0,5)}];
 }).sort((a,b)=>b.recentCount/a.priorCount-a.recentCount/b.priorCount||a.variant.localeCompare(b.variant));
}
export async function getMarketPatterns(now=new Date()){
 try{
  const {getCloudflareContext}=await import("@opennextjs/cloudflare");
  const {env}=await getCloudflareContext({async:true});const db=(env as {SALES_DB?:Db}).SALES_DB;
  if(!db)return null;
  const start=new Date(+now-28*86400000).toISOString().slice(0,10);
  const {results}=await db.prepare(patternQuery).bind(start,now.toISOString().slice(0,10),now.toISOString()).all<PatternSale>();
  // Never classify a truncated sales sample as an acceleration.
  if(results.length>5000)return {partial:true,items:[]};
  return {partial:false,items:recognizePatterns(results,now.toISOString()).slice(0,15)};
 }catch{return null;}
}
