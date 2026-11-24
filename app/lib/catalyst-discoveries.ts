import {classifyCatalyst} from "./catalyst-intelligence";
type Db={prepare(sql:string):{bind(...args:string[]):{all<T>():Promise<{results:T[]}>}}};
type Discovery={source_url:string;publisher:string;title:string;first_seen_at:string;payload_sha256:string};
type Scan={observed_at:string;status:"OK"|"EMPTY"|"FAILED";discovered:number};
export async function getCatalystDiscoveries(now=new Date()){
 try{
 const {getCloudflareContext}=await import("@opennextjs/cloudflare");
 const {env}=await getCloudflareContext({async:true});
 const db=(env as {SALES_DB?:Db}).SALES_DB;if(!db)return null;
 const stamp=now.toISOString();
 const [leads,scans]=await Promise.all([
 db.prepare("SELECT * FROM catalyst_discoveries WHERE first_seen_at<=? ORDER BY first_seen_at DESC,source_url LIMIT 40").bind(stamp).all<Discovery>(),
 db.prepare("SELECT observed_at,status,discovered FROM catalyst_scan_runs WHERE publisher=? AND observed_at<=? ORDER BY observed_at DESC,run_id DESC LIMIT 1").bind("Wizards of the Coast",stamp).all<Scan>()
 ]);
 const items=leads.results.filter(p=>/^https:\/\/magic\.wizards\.com\/en\/news\/(?:announcements|feature)\/[a-z0-9-]+$/.test(p.source_url)&&/^[a-f0-9]{64}$/.test(p.payload_sha256)).map(p=>({...p,kind:classifyCatalyst(p.title)}));
 return {items,scan:scans.results[0]??null};
 }catch{return null;}
}
