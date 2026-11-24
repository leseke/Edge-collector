import {candidateMatches} from "../../cloud/collector/src/commercial-parser.mjs";
import {classifyCatalyst} from "./catalyst-intelligence";
type Db={prepare(sql:string):{bind(...args:string[]):{all<T>():Promise<{results:T[]}>}}};
type Discovery={source_url:string;publisher:string;title:string;first_seen_at:string;payload_sha256:string;investigation_status:string|null;headline:string|null;description:string|null;published_at:string|null;investigated_at:string|null};
type Scan={observed_at:string;status:"OK"|"EMPTY"|"FAILED";discovered:number};
export async function getCatalystDiscoveries(now=new Date()){
 try{
 const {getCloudflareContext}=await import("@opennextjs/cloudflare");
 const {env}=await getCloudflareContext({async:true});
 const db=(env as {SALES_DB?:Db}).SALES_DB;if(!db)return null;
 const stamp=now.toISOString();
 const [leads,scans,commercial]=await Promise.all([
 db.prepare(`SELECT d.*,i.status AS investigation_status,i.headline,i.description,i.published_at,i.observed_at AS investigated_at FROM catalyst_discoveries d LEFT JOIN catalyst_investigations i ON i.source_url=d.source_url AND i.observed_at=(SELECT MAX(x.observed_at) FROM catalyst_investigations x WHERE x.source_url=d.source_url) WHERE d.first_seen_at<=? ORDER BY d.first_seen_at DESC,d.source_url LIMIT 40`).bind(stamp).all<Discovery>(),
 db.prepare("SELECT observed_at,status,discovered FROM catalyst_scan_runs WHERE publisher=? AND observed_at<=? ORDER BY observed_at DESC,run_id DESC LIMIT 1").bind("Wizards of the Coast",stamp).all<Scan>(),
 db.prepare("SELECT observed_at,status,evidence_json FROM commercial_research_observations WHERE source_url=? AND observed_at<=? ORDER BY observed_at DESC LIMIT 1").bind("https://www.play-in.com/fr/gamme/1/magic/catalogue",stamp).all<{observed_at:string;status:string;evidence_json:string}>()
 ]);
 const market= commercial.results[0]??null;
 const raw:unknown=market?.status==="READ"?JSON.parse(market.evidence_json):[];
 const candidates=Array.isArray(raw)?raw.filter((p):p is {url:string;title:string}=>p&&typeof p.title==="string"&&typeof p.url==="string"&&/^https:\/\/www\.play-in\.com\/fr\/produit\//.test(p.url)):[];
 const items=leads.results.filter(p=>/^https:\/\/magic\.wizards\.com\/en\/news\/(?:announcements|feature)\/[a-z0-9-]+$/.test(p.source_url)&&/^[a-f0-9]{64}$/.test(p.payload_sha256)).map(p=>({...p,kind:classifyCatalyst(p.title),commercialCandidates:candidateMatches(p.headline??p.title,candidates)}));
 return {items,scan:scans.results[0]??null,commercial:market?{observedAt:market.observed_at,status:market.status}:null};
 }catch{return null;}
}
