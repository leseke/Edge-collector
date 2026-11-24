import {productOffer} from "./commercial-offer.mjs";
import {candidateMatches,merchantSources} from "./commercial-parser.mjs";
import {readBoundedText} from "./bounded.mjs";
export async function collectCommercialOffers(db:D1Database,request=fetch,now=new Date()){
 const stamp=now.toISOString();
 for(const source of merchantSources){
 const catalog=await db.prepare("SELECT evidence_json,status FROM commercial_research_observations WHERE source_url=? ORDER BY observed_at DESC LIMIT 1").bind(source.catalog).first<{evidence_json:string;status:string}>();
 if(!catalog||catalog.status!=="READ")continue;
 const items=JSON.parse(catalog.evidence_json);
 const {results}=await db.prepare("SELECT headline FROM catalyst_investigations WHERE status='READ' AND headline IS NOT NULL ORDER BY observed_at DESC LIMIT 30").all<{headline:string}>();
 const urls=new Set<string>();
 for(const row of results)for(const item of candidateMatches(row.headline,items))if(source.product.test(item.url))urls.add(item.url);
 for(const url of [...urls].slice(0,3)){
  let status="FAILED",hash:string|null=null,evidence="[]";
  try{
   const response=await request(url,{redirect:"error",signal:AbortSignal.timeout(8000),headers:{Accept:"text/html"}});
   if(!response.ok||!response.headers.get("content-type")?.includes("text/html"))throw new Error("source_unavailable");
   const html=await readBoundedText(response,2_000_000),offer=productOffer(html);
   if(!offer)throw new Error("ambiguous_or_missing_product");
   hash=[...new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(html)))].map(b=>b.toString(16).padStart(2,"0")).join("");
   status="READ";evidence=JSON.stringify(offer);
  }catch{}
  await db.prepare("INSERT OR IGNORE INTO commercial_research_observations(source_url,observed_at,merchant,status,evidence_json,payload_sha256) VALUES (?,?,?,?,?,?)").bind(url,stamp,source.merchant,status,evidence,hash).run();
 }
 }
}
