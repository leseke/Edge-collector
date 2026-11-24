// Retrospective, not a simulated trade. One first signal per exact variant and reason.
type Db={prepare(sql:string):{bind(...args:string[]):{all<T>():Promise<{results:T[]}>}}};
type Outcome={reason:string;lot_id:string;variant_key:string;observed_at:string;median_cents:number;future_count:number;future_median:number|null;control_count?:number;control_change?:number|null};
export const learningHorizons=[7,30,90,365] as const;
export type LearningHorizon=typeof learningHorizons[number];
export function learningHorizon(value:unknown):LearningHorizon {
 return learningHorizons.find(n=>String(n)===value)??30;
}
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
 WHERE s.sold_day>substr(c.observed_at,1,10) AND s.sold_day<=date(c.observed_at,?)
 AND s.collected_at<=? AND s.lot_id<>'gcc-'||c.lot_id AND s.price_cents>0
 AND s.source_url='https://gradedcardcenter.com/item/'||substr(s.lot_id,5) AND s.lot_id LIKE 'gcc-%'
), medians AS (
 SELECT reason,variant_key,MAX(n) AS future_count,AVG(CASE WHEN position IN ((n+1)/2,(n+2)/2) THEN price_cents END) AS future_median
 FROM prices GROUP BY reason,variant_key
)
SELECT c.reason,c.lot_id,c.variant_key,c.observed_at,c.median_cents,COALESCE(m.future_count,0) AS future_count,m.future_median
FROM cohort c LEFT JOIN medians m USING(reason,variant_key)`;
 // Controls must have been observed and assessed before the signal, not selected using future prices.
export const controlQuery=`
WITH anchor AS (
 SELECT ? AS stamp,? AS variant,? AS baseline,? AS horizon,? AS report_at
), candidates AS (
 SELECT e.variant_key,e.median_cents,e.comparable_count,
 ROW_NUMBER() OVER(PARTITION BY e.variant_key ORDER BY e.observed_at DESC,e.cycle DESC,e.page DESC,e.lot_id) AS rn
 FROM gcc_opportunity_events e CROSS JOIN anchor a
 WHERE e.observed_at<=a.stamp AND e.observed_at>=strftime('%Y-%m-%dT%H:%M:%fZ',a.stamp,'-7 days')
 AND e.variant_key<>a.variant AND e.median_cents BETWEEN CAST(a.baseline AS REAL)*0.5 AND CAST(a.baseline AS REAL)*2
 AND e.comparable_count>=3 AND e.status='NO_DISCOUNT'
 AND NOT EXISTS (SELECT 1 FROM gcc_research_alerts x JOIN gcc_opportunity_events y USING(lot_id,cycle,page)
 WHERE y.variant_key=e.variant_key AND x.observed_at BETWEEN strftime('%Y-%m-%dT%H:%M:%fZ',a.stamp,'-30 days') AND a.stamp)
), selected AS (
 SELECT variant_key,median_cents FROM candidates CROSS JOIN anchor WHERE rn=1
 ORDER BY ABS(median_cents-CAST(baseline AS REAL)),variant_key LIMIT 10
), prices AS (
 SELECT c.variant_key,c.median_cents,s.price_cents,
 ROW_NUMBER() OVER(PARTITION BY c.variant_key ORDER BY s.price_cents,s.lot_id) AS pos,
 COUNT(*) OVER(PARTITION BY c.variant_key) AS n
 FROM selected c JOIN paid_market_sales s USING(variant_key) CROSS JOIN anchor a
 WHERE s.sold_day>substr(a.stamp,1,10) AND s.sold_day<=date(a.stamp,a.horizon)
 AND s.collected_at<=a.report_at AND s.price_cents>0
 AND s.lot_id LIKE 'gcc-%' AND s.source_url='https://gradedcardcenter.com/item/'||substr(s.lot_id,5)
), changes AS (
 SELECT variant_key,100.0*(AVG(CASE WHEN pos IN ((n+1)/2,(n+2)/2) THEN price_cents END)-median_cents)/median_cents AS change
 FROM prices GROUP BY variant_key,median_cents HAVING MAX(n)>=3
)
SELECT change FROM changes ORDER BY change`;
export function median(values:number[]){
 const sorted=[...values].sort((a,b)=>a-b),n=sorted.length;
 return n?(sorted[Math.floor((n-1)/2)]+sorted[Math.floor(n/2)])/2:null;
}
export function summarizeRelative(rows:Outcome[]){
 const groups=new Map<string,{reason:string;paired:number;excess:number[]}>();
 for(const r of rows){
  const g=groups.get(r.reason)??{reason:r.reason,paired:0,excess:[]};
  if(r.future_count>=3&&r.future_median!==null&&r.median_cents>0&&(r.control_count??0)>=3&&r.control_change!=null){
   g.paired++;g.excess.push(100*(r.future_median-r.median_cents)/r.median_cents-r.control_change);
  }
  groups.set(r.reason,g);
 }
 return [...groups.values()].map(g=>({reason:g.reason,paired:g.paired,medianExcess:median(g.excess)}));
}
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
export async function getLearningReport(horizon:LearningHorizon=30,now=new Date()){
 try{
  const {getCloudflareContext}=await import("@opennextjs/cloudflare");
  const {env}=await getCloudflareContext({async:true});
  const db=(env as {SALES_DB?:Db}).SALES_DB;if(!db)return null;
  const start=new Date(+now-(180+horizon)*86400000).toISOString();
  const cutoff=new Date(+now-(horizon+1)*86400000).toISOString();
  const {results}=await db.prepare(learningQuery).bind(start,cutoff,'+'+horizon+' days',now.toISOString()).all<Outcome>();
  const sample=results.slice(0,100);
  // Bound the number of additional database queries per page.
  const paired=sample.filter(r=>r.future_count>=3&&r.future_median!==null).slice(0,12);
  const controls=await Promise.all(paired.map(async r=>{
   const {results:matches}=await db.prepare(controlQuery).bind(r.observed_at,r.variant_key,String(r.median_cents),'+'+horizon+' days',now.toISOString()).all<{change:number}>();
   return {...r,control_count:matches.length,control_change:median(matches.map(m=>m.change))};
  }));
  return {groups:summarizeOutcomes(sample),relative:summarizeRelative(controls),partial:results.length>100,controlSample:paired.length};
 }catch{return null;}
}
