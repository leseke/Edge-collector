type Db={prepare(sql:string):{bind(...args:string[]):{all<T>():Promise<{results:T[]}>}}};
export type SupplyRow={variant_key:string;title:string;prior_count:number;current_count:number;prior_at:string;current_at:string};
export const supplyQuery=`
WITH latest AS (
 SELECT cycle,completed_at FROM gcc_complete_cycles WHERE kind='fixed' AND completed_at BETWEEN ? AND ?
 ORDER BY completed_at DESC,cycle DESC LIMIT 1
), prior AS (
 SELECT c.cycle,c.completed_at FROM gcc_complete_cycles c CROSS JOIN latest l
 WHERE c.kind='fixed' AND c.completed_at BETWEEN strftime('%Y-%m-%dT%H:%M:%fZ',l.completed_at,'-14 days') AND strftime('%Y-%m-%dT%H:%M:%fZ',l.completed_at,'-7 days')
 ORDER BY c.completed_at DESC,c.cycle DESC LIMIT 1
), observations AS (
 SELECT o.*,ROW_NUMBER() OVER(PARTITION BY o.cycle,o.lot_id ORDER BY o.page DESC) AS rn
 FROM gcc_offer_observations o WHERE o.kind='fixed' AND o.cycle IN (SELECT cycle FROM latest UNION SELECT cycle FROM prior)
), counts AS (
 SELECT variant_key,MAX(title) AS title,
 SUM(CASE WHEN cycle=(SELECT cycle FROM prior) THEN 1 ELSE 0 END) AS prior_count,
 SUM(CASE WHEN cycle=(SELECT cycle FROM latest) THEN 1 ELSE 0 END) AS current_count
 FROM observations WHERE rn=1 AND variant_key IS NOT NULL GROUP BY variant_key
)
SELECT counts.*,prior.completed_at AS prior_at,latest.completed_at AS current_at
FROM counts CROSS JOIN prior CROSS JOIN latest
WHERE prior_count>=5 AND current_count<=prior_count*0.7
ORDER BY 1.0*current_count/prior_count,variant_key LIMIT 100`;
export function supplyContraction(row:SupplyRow){return 100*(row.prior_count-row.current_count)/row.prior_count;}
export async function getSupplyPatterns(now=new Date()){
 try{
  const {getCloudflareContext}=await import("@opennextjs/cloudflare");
  const {env}=await getCloudflareContext({async:true});const db=(env as {SALES_DB?:Db}).SALES_DB;
  if(!db)return null;
  const {results}=await db.prepare(supplyQuery).bind(new Date(+now-48*3600000).toISOString(),now.toISOString()).all<SupplyRow>();
  return results;
 }catch{return null;}
}
