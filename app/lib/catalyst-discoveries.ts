import {candidateMatches,merchantSources,comparableOffers} from "../../cloud/collector/src/commercial-parser.mjs";
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
 const [leads,scans,commercial,offers]=await Promise.all([
 db.prepare(`SELECT d.*,i.status AS investigation_status,i.headline,i.description,i.published_at,i.observed_at AS investigated_at FROM catalyst_discoveries d LEFT JOIN catalyst_investigations i ON i.source_url=d.source_url AND i.observed_at=(SELECT MAX(x.observed_at) FROM catalyst_investigations x WHERE x.source_url=d.source_url) WHERE d.first_seen_at<=? ORDER BY d.first_seen_at DESC,d.source_url LIMIT 40`).bind(stamp).all<Discovery>(),
 db.prepare("SELECT observed_at,status,discovered FROM catalyst_scan_runs WHERE publisher=? AND observed_at<=? ORDER BY observed_at DESC,run_id DESC LIMIT 1").bind("Wizards of the Coast",stamp).all<Scan>(),
 db.prepare(`SELECT o.source_url,o.merchant,o.observed_at,o.status,o.evidence_json FROM commercial_research_observations o WHERE o.source_url IN (?,?) AND o.observed_at<=? AND o.observed_at=(SELECT MAX(x.observed_at) FROM commercial_research_observations x WHERE x.source_url=o.source_url AND x.observed_at<=?)`).bind(merchantSources[0].catalog,merchantSources[1].catalog,stamp,stamp).all<{source_url:string;merchant:string;observed_at:string;status:string;evidence_json:string}>(),
 db.prepare(`SELECT o.source_url,o.merchant,o.observed_at,o.status,o.evidence_json FROM commercial_research_observations o
 WHERE (o.source_url LIKE 'https://www.play-in.com/fr/produit/%' OR o.source_url LIKE 'https://www.philibertnet.com/fr/%.html') AND o.observed_at<=?
 AND o.observed_at=(SELECT MAX(x.observed_at) FROM commercial_research_observations x WHERE x.source_url=o.source_url AND x.observed_at<=?)
 ORDER BY o.observed_at DESC,o.source_url LIMIT 100`).bind(stamp,stamp).all<{source_url:string;merchant:string;observed_at:string;status:string;evidence_json:string}>()
 ]);
 const candidates=commercial.results.flatMap(market=>{
 const source=merchantSources.find(s=>s.catalog===market.source_url);
 const raw:unknown=market.status==="READ"&&+now-Date.parse(market.observed_at)<=48*3600000?JSON.parse(market.evidence_json):[];
 return Array.isArray(raw)&&source?raw.filter((p):p is {url:string;title:string}=>p&&typeof p.title==="string"&&typeof p.url==="string"&&source.product.test(p.url)):[];
 });
 const verified=new Map(offers.results.map(o=>{
 let evidence:{gtin?:string|null;name?:string;sku?:string|null;priceCents?:number|null;currency?:string|null;availability?:string}={};
 if(o.status==="READ"){try{evidence=JSON.parse(o.evidence_json);}catch{}}
 return [o.source_url,{...evidence,merchant:o.merchant,url:o.source_url,observedAt:o.observed_at,status:o.status,fresh:+now-Date.parse(o.observed_at)<=48*3600000}] as const;
 }));
 const items=leads.results.filter(p=>/^https:\/\/magic\.wizards\.com\/en\/news\/(?:announcements|feature)\/[a-z0-9-]+$/.test(p.source_url)&&/^[a-f0-9]{64}$/.test(p.payload_sha256)).map(p=>({...p,kind:classifyCatalyst(p.title),commercialCandidates:(candidateMatches(p.headline??p.title,candidates) as {url:string;title:string;overlap:string[]}[]).map(c=>({...c,offer:verified.get(c.url)??null}))}));
 return {items,scan:scans.results[0]??null,commercial:commercial.results.map(m=>({merchant:m.merchant,observedAt:m.observed_at,status:m.status})),comparisons:comparableOffers([...verified.values()].filter(o=>merchantSources.some(s=>s.merchant===o.merchant&&s.product.test(o.url))))};
 }catch{return null;}
}
