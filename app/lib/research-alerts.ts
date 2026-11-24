export type AlertReason = "NEW_OPPORTUNITY" | "STATUS_IMPROVED" | "PRICE_DROP" | "REAPPEARED";
export type ResearchAlert = {
 lot_id:string; cycle:number; page:number; observed_at:string; reason:AlertReason;
 asking_cents:number; previous_cents:number|null; status:string; title:string;
 variant_key:string|null; median_cents:number|null; comparable_count:number;
 headroom_cents:number|null; resale_fee_percent:number; evidence_json:string;
 paid_day:string|null; latest_seen:string|null; latest_visibility:string|null;
};
type Database = {prepare(sql:string):{bind(...args:(string|number)[]):{all<T>():Promise<{results:T[]}>}}};
export const researchAlertQuery = `
SELECT a.*,e.title,e.variant_key,e.median_cents,e.comparable_count,e.headroom_cents,e.resale_fee_percent,e.evidence_json,
 (SELECT s.sold_day FROM paid_market_sales s WHERE s.lot_id='gcc-'||a.lot_id AND s.collected_at<=?) AS paid_day,
 (SELECT MAX(o.observed_at) FROM gcc_offer_observations o WHERE o.kind='fixed' AND o.lot_id=a.lot_id AND o.observed_at<=?) AS latest_seen,
 (SELECT l.event FROM gcc_lifecycle_events l WHERE l.lot_id=a.lot_id AND l.observed_at<=? ORDER BY l.cycle DESC,l.observed_at DESC LIMIT 1) AS latest_visibility
FROM gcc_research_alerts a JOIN gcc_opportunity_events e
 ON e.lot_id=a.lot_id AND e.cycle=a.cycle AND e.page=a.page
WHERE a.observed_at<=? AND (?='all' OR a.reason=?)
ORDER BY a.observed_at DESC,a.lot_id,a.cycle DESC,a.page DESC LIMIT ? OFFSET ?`;
export function alertFilter(value:unknown): AlertReason|"all" {
 return value==="NEW_OPPORTUNITY"||value==="STATUS_IMPROVED"||value==="PRICE_DROP"||value==="REAPPEARED"?value:"all";
}
export function alertPage(value:unknown) {
 return typeof value==="string"&&/^[1-9][0-9]{0,3}$/.test(value)?Math.min(Number(value),1000):1;
}
export function alertEvidence(row:ResearchAlert) {
 try {
  const raw:unknown=JSON.parse(row.evidence_json);
  if(!Array.isArray(raw))return [];
  return raw.filter((s):s is {id:string;day:string;cents:number;source:string} =>
   s && typeof s.id==="string" && /^gcc-[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(s.id)
   && s.source==="https://gradedcardcenter.com/item/"+s.id.slice(4)
   && typeof s.day==="string" && /^\d{4}-\d{2}-\d{2}$/.test(s.day)
   && Number.isSafeInteger(s.cents)&&s.cents>0).slice(0,10);
 } catch{return [];}
}
export async function readResearchAlerts(db:Database,filter:AlertReason|"all",page:number,now=new Date()){
 const stamp=now.toISOString();
 const {results}=await db.prepare(researchAlertQuery).bind(stamp,stamp,stamp,stamp,filter,filter,21,(page-1)*20).all<ResearchAlert>();
 return {items:results.slice(0,20),hasNext:results.length>20};
}
export async function getResearchAlerts(filter:AlertReason|"all",page:number){
 try{
  const {getCloudflareContext}=await import("@opennextjs/cloudflare");
  const {env}=await getCloudflareContext({async:true});
  const db=(env as {SALES_DB?:Database}).SALES_DB;
  return db?await readResearchAlerts(db,filter,page):null;
 }catch{return null;}
}
