type Db={prepare(sql:string):{bind(...args:string[]):{all<T>():Promise<{results:T[]}>}}};
export type AbsorptionRow={variant_key:string;title:string;cohort_count:number;paid_count:number;median_delay_days:number|null};
export const absorptionQuery=`
WITH first_seen AS (
 SELECT o.lot_id,MIN(o.observed_at) AS first_at
 FROM gcc_offer_observations o WHERE o.kind='fixed' AND o.observed_at<=?
 GROUP BY o.lot_id
), cohort AS (
 SELECT f.lot_id,f.first_at,o.variant_key,o.title,
 ROW_NUMBER() OVER(PARTITION BY f.lot_id ORDER BY o.cycle,o.page) AS rn
 FROM first_seen f JOIN gcc_offer_observations o ON o.kind='fixed' AND o.lot_id=f.lot_id AND o.observed_at=f.first_at
 WHERE f.first_at BETWEEN ? AND ? AND o.variant_key IS NOT NULL
 AND EXISTS (SELECT 1 FROM gcc_complete_cycles c WHERE c.kind='fixed'
 AND c.completed_at BETWEEN strftime('%Y-%m-%dT%H:%M:%fZ',f.first_at,'-48 hours') AND f.first_at
 AND c.completed_at<f.first_at)
), outcomes AS (
 SELECT c.variant_key,c.title,c.lot_id,
 CASE WHEN s.sold_day IS NOT NULL THEN julianday(s.sold_day)-julianday(substr(c.first_at,1,10)) END AS delay
 FROM cohort c LEFT JOIN paid_market_sales s ON s.lot_id='gcc-'||c.lot_id
 AND s.variant_key=c.variant_key AND s.source_url='https://gradedcardcenter.com/item/'||c.lot_id
 AND s.collected_at<=? AND s.sold_day>substr(c.first_at,1,10)
 AND s.sold_day<=date(c.first_at,'+14 days')
 WHERE c.rn=1
), ranked AS (
 SELECT variant_key,delay,ROW_NUMBER() OVER(PARTITION BY variant_key ORDER BY delay,lot_id) AS pos,
 COUNT(*) OVER(PARTITION BY variant_key) AS n FROM outcomes WHERE delay IS NOT NULL
), medians AS (
 SELECT variant_key,AVG(CASE WHEN pos IN ((n+1)/2,(n+2)/2) THEN delay END) AS median_delay_days
 FROM ranked GROUP BY variant_key
), totals AS (
 SELECT variant_key,MAX(title) AS title,COUNT(*) AS cohort_count,COUNT(delay) AS paid_count
 FROM outcomes GROUP BY variant_key HAVING COUNT(*)>=5
)
SELECT totals.*,medians.median_delay_days FROM totals LEFT JOIN medians USING(variant_key)
ORDER BY 1.0*paid_count/cohort_count DESC,cohort_count DESC,variant_key LIMIT 30`;
export function absorptionRate(row:AbsorptionRow){return row.cohort_count>0?100*row.paid_count/row.cohort_count:null;}
export async function getAbsorptionReport(now=new Date()){
 try{
 const {getCloudflareContext}=await import("@opennextjs/cloudflare");
 const {env}=await getCloudflareContext({async:true});const db=(env as {SALES_DB?:Db}).SALES_DB;
 if(!db)return null;
 const stamp=now.toISOString(),start=new Date(+now-75*86400000).toISOString(),cutoff=new Date(+now-15*86400000).toISOString();
 const {results}=await db.prepare(absorptionQuery).bind(stamp,start,cutoff,stamp).all<AbsorptionRow>();
 return results;
 }catch{return null;}
}
