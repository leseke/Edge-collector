type Db={prepare(sql:string):{bind(...args:(string|number)[]):{all<T>():Promise<{results:T[]}>}}};
export type FollowedLot={lot_id:string;title:string;variant_key:string|null;first_seen:string;observed_at:string;initial_cents:number;asking_cents:number;median_cents:number|null;headroom_cents:number|null;comparable_count:number;status:string;paid_day:string|null;latest_visibility:string|null;latest_seen:string|null};
export const followedLotsQuery=`
WITH tracked AS (
 SELECT lot_id,MIN(observed_at) AS first_seen FROM gcc_opportunity_events
 WHERE status='INVESTIGATE' AND observed_at<=? GROUP BY lot_id
), latest AS (
 SELECT e.*,t.first_seen,ROW_NUMBER() OVER(PARTITION BY e.lot_id ORDER BY e.cycle DESC,e.page DESC) AS rn
 FROM gcc_opportunity_events e JOIN tracked t ON t.lot_id=e.lot_id WHERE e.observed_at<=?
)
SELECT e.lot_id,e.title,e.variant_key,e.first_seen,e.observed_at,e.asking_cents,e.median_cents,e.headroom_cents,e.comparable_count,e.status,
 (SELECT x.asking_cents FROM gcc_opportunity_events x WHERE x.lot_id=e.lot_id AND x.status='INVESTIGATE' AND x.observed_at<=? ORDER BY x.observed_at,x.cycle,x.page LIMIT 1) AS initial_cents,
 (SELECT MIN(s.sold_day) FROM paid_market_sales s WHERE s.lot_id='gcc-'||e.lot_id AND s.collected_at<=?) AS paid_day,
 (SELECT l.event FROM gcc_lifecycle_events l WHERE l.lot_id=e.lot_id AND l.observed_at<=? ORDER BY l.cycle DESC,l.observed_at DESC LIMIT 1) AS latest_visibility,
 (SELECT MAX(o.observed_at) FROM gcc_offer_observations o WHERE o.kind='fixed' AND o.lot_id=e.lot_id AND o.observed_at<=?) AS latest_seen
FROM latest e WHERE e.rn=1 ORDER BY e.observed_at DESC,e.lot_id LIMIT ? OFFSET ?`;
export function followPage(value:unknown){return typeof value==="string"&&/^[1-9][0-9]{0,3}$/.test(value)?Math.min(Number(value),1000):1;}
export async function readFollowedLots(db:Db,page:number,now=new Date()){
 const t=now.toISOString();
 const {results}=await db.prepare(followedLotsQuery).bind(t,t,t,t,t,t,21,(page-1)*20).all<FollowedLot>();
 return {items:results.slice(0,20),hasNext:results.length>20};
}
export async function getFollowedLots(page:number){
 try{const {getCloudflareContext}=await import("@opennextjs/cloudflare");const {env}=await getCloudflareContext({async:true});const db=(env as {SALES_DB?:Db}).SALES_DB;return db?await readFollowedLots(db,page):null;}catch{return null;}
}
