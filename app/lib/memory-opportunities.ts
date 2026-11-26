type Db={prepare(sql:string):{bind(...args:(string|number)[]):{all<T>():Promise<{results:T[]}>}}};
export type MemoryOpportunity={lot_id:string;title:string;variant_key:string;observed_at:string;asking_cents:number;median_cents:number;headroom_cents:number;comparable_count:number;resale_fee_percent:number;status:string;image_url:string|null;evidence_json:string};
export const currentOpportunityCte=`
WITH latest AS (
 SELECT e.* FROM gcc_opportunity_events e
 WHERE e.observed_at BETWEEN ? AND ?
 AND NOT EXISTS (SELECT 1 FROM gcc_opportunity_events n WHERE n.lot_id=e.lot_id AND n.observed_at<=? AND (n.cycle>e.cycle OR (n.cycle=e.cycle AND n.page>e.page)))
), eligible AS (
 SELECT e.* FROM latest e
 WHERE e.status IN ('INVESTIGATE','THIN_MARGIN') AND e.variant_key IS NOT NULL
 AND e.median_cents>e.asking_cents AND e.comparable_count>=2 AND e.headroom_cents IS NOT NULL
 AND NOT EXISTS (SELECT 1 FROM paid_market_sales s WHERE s.lot_id='gcc-'||e.lot_id AND s.collected_at<=?)
 AND NOT EXISTS (SELECT 1 FROM gcc_lifecycle_events l WHERE l.lot_id=e.lot_id AND l.event='NOT_SEEN' AND l.cycle>=e.cycle AND l.observed_at<=?)
 AND EXISTS (SELECT 1 FROM gcc_offer_observations o WHERE o.kind='fixed' AND o.lot_id=e.lot_id AND o.cycle=e.cycle AND o.page=e.page AND o.variant_key=e.variant_key AND o.price_cents=e.asking_cents)
)`;
export async function readMemoryOpportunities(db:Db,now=new Date()){
 const stamp=now.toISOString(),cutoff=new Date(+now-48*3600000).toISOString();
 const args=[cutoff,stamp,stamp,stamp,stamp];
 const [stats,ranked,coverage]=await Promise.all([
 db.prepare(currentOpportunityCte+" SELECT COUNT(*) AS candidates,COALESCE(SUM(CASE WHEN headroom_cents>0 THEN 1 ELSE 0 END),0) AS positive FROM eligible").bind(...args).all<{candidates:number;positive:number}>(),
 db.prepare(currentOpportunityCte+` SELECT e.*, (SELECT i.image_url FROM gcc_lot_images i WHERE i.lot_id=e.lot_id AND i.observed_at<=? ORDER BY i.observed_at DESC,i.image_url LIMIT 1) AS image_url FROM eligible e ORDER BY (headroom_cents>0) DESC,1.0*(median_cents-asking_cents)/median_cents DESC,comparable_count DESC,lot_id LIMIT 12`).bind(...args,stamp).all<MemoryOpportunity>(),
 db.prepare("SELECT COUNT(DISTINCT lot_id) AS examined,MAX(observed_at) AS latest FROM gcc_opportunity_events WHERE observed_at BETWEEN ? AND ?").bind(cutoff,stamp).all<{examined:number;latest:string|null}>()
 ]);
 return {items:ranked.results,candidates:stats.results[0]?.candidates??0,positive:stats.results[0]?.positive??0,examined:coverage.results[0]?.examined??0,latest:coverage.results[0]?.latest??null};
}
export async function getMemoryOpportunities(){
 try{const {getCloudflareContext}=await import("@opennextjs/cloudflare");const {env}=await getCloudflareContext({async:true});const db=(env as {SALES_DB?:Db}).SALES_DB;return db?await readMemoryOpportunities(db):null;}catch{return null;}
}
