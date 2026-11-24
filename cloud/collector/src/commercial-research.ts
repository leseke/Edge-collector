import {merchantSources} from "./commercial-parser.mjs";
import {readBoundedText} from "./bounded.mjs";
export async function collectCommercialResearch(db:D1Database,request=fetch,now=new Date()){
 const stamp=now.toISOString();
 for(const source of merchantSources){
 const url=source.catalog;
 let status="FAILED",hash:string|null=null,evidence="[]";
 try{
  const response=await request(url,{redirect:"error",signal:AbortSignal.timeout(8000),headers:{Accept:"text/html"}});
  if(!response.ok||!response.headers.get("content-type")?.includes("text/html"))throw new Error("source_unavailable");
  const html=await readBoundedText(response,2_000_000),items=source.parse(html);
  if(!items.length)throw new Error("no_candidate_links");
  hash=[...new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(html)))].map(b=>b.toString(16).padStart(2,"0")).join("");
  status="READ";evidence=JSON.stringify(items);
 }catch{}
 await db.prepare("INSERT OR IGNORE INTO commercial_research_observations(source_url,observed_at,merchant,status,evidence_json,payload_sha256) VALUES (?,?,?,?,?,?)").bind(url,stamp,source.merchant,status,evidence,hash).run();
 }
}
