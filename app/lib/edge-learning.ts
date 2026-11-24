// Retrospective, not a simulated trade. One first signal per exact variant and reason.
type Db={prepare(sql:string):{bind(...args:string[]):{all<T>():Promise<{results:T[]}>}}};
type Outcome={reason:string;lot_id:string;variant_key:string;observed_at:string;median_cents:number;future_count:number;future_median:number|null};
export const learningQuery=`
WITH eligible AS (
 SELECT a.reason,a.lot_id,a.observed_at,e.variant_key,e.median_cents,
 ROW_NUMBER() OVER(PARTITION BY a.reason,e.variant_key ORDER BY a.observed_at,a.lot_id,a.cycle,a.page) AS rn
 FROM gcc_research_alerts a JOIN gcc_opportunity_events e USING(lot_id,cycle,page)
 WHERE e.variant_key IS NOT NULL AND e.median_cents>0 AND e.comparable_count>=2
 AND a.observed_at BETWEEN ? AND ?
), cohort AS (
 SELECT * FROM eligible WHERE rn=1 ORDER BY observed_at DESC,lot_id LIMIT 101
), prices AS (
 SELECT c.reason,c.lot_id,c.variant_key,c.observed_at,c.median_cents,s.price_cents,
 ROW_NUMBER() OVER(PARTITION BY c.reason,c.variant_key ORDER BY s.price_cents,s.lot_id) AS position,
 COUNT(*) OVER(PARTITION BY c.reason,c.variant_key) AS n
 FROM cohort c JOIN paid_market_sales s ON s.variant_key=c.variant_key
 WHERE s.sold_day>substr(c.observed_at,1,10) AND s.sold_day<=date(c.observed_at,'+30 days')
 AND s.collected_at<=? AND s.lot_id<>'gcc-'||c.lot_id AND s.price_cents>0
 AND s.source_url='https://gradedcardcenter.com/item/'||substr(s.lot_id,5) AND s.lot_id LIKE 'gcc-%'
), medians AS (
 SELECT reason,variant_key,MAX(n) AS future_count,AVG(CASE WHEN position IN ((n+1)/2,(n+2)/2) THEN price_cents END) AS future_median
 FROM prices GROUP BY reason,variant_key
)
SELECT c.reason,c.lot_id,c.variant_key,c.observed_at,c.median_cents,COALESCE(m.future_count,0) AS future_count,m.future_median
FROM cohort c LEFT JOIN medians m USING(reason,variant_key)`;
export function summarizeOutcomes(rows:Outcome[]){
 const groups=new Map<string,{reason:string;eligible:number;evaluable:number;up:number;flat:number;down:number;changes:number[]}>();
 for(const row of rows){
  const g=groups.get(row.reason)??{reason:row.reason,eligible:0,evaluable:0,up:0,flat:0,down:0,changes:[]};
  g.eligible++;
  if(row.future_count>=3&&row.future_median!==null&&row.median_cents>0){
   const change=100*(row.future_median-row.median_cents)/row.median_cents;
   g.evaluable++;g.changes.push(change);
   if(change>5)g.up++;else if(change< -5)g.down++;else g.flat++;
  }
  groups.set(row.reason,g);
 }
 return [...groups.values()].map(({changes,...g})=>{
  changes.sort((a,b)=>a-b);const n=changes.length;
  return {...g,medianChange:n?(changes[Math.floor((n-1)/2)]+changes[Math.floor(n/2)])/2:null};
 });
}
export async function getLearningReport(now=new Date()){
 try{
  const {getCloudflareContext}=await import("@opennextjs/cloudflare");
  const {env}=await getCloudflareContext({async:true});
  const db=(env as {SALES_DB?:Db}).SALES_DB;if(!db)return null;
  const start=new Date(+now-180*86400000).toISOString();
  const cutoff=new Date(+now-31*86400000).toISOString();
  const {results}=await db.prepare(learningQuery).bind(start,cutoff,now.toISOString()).all<Outcome>();
  return {groups:summarizeOutcomes(results.slice(0,100)),partial:results.length>100};
 }catch{return null;}
}
