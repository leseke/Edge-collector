import {publisherMetadata} from "./catalyst-metadata.mjs";
import {readBoundedText} from "./bounded.mjs";
export async function investigateCatalysts(db:D1Database,request=fetch,now=new Date()){
 const stamp=now.toISOString(),retryBefore=new Date(+now-86400000).toISOString();
 const {results}=await db.prepare(`SELECT d.source_url FROM catalyst_discoveries d
 WHERE NOT EXISTS (SELECT 1 FROM catalyst_investigations i WHERE i.source_url=d.source_url AND (i.status='READ' OR i.observed_at>=?))
 ORDER BY d.first_seen_at,d.source_url LIMIT 4`).bind(retryBefore).all<{source_url:string}>();
 for(const row of results){
  const url=row.source_url;
  if(!/^https:\/\/magic\.wizards\.com\/en\/news\/(?:announcements|feature)\/[a-z0-9-]+$/.test(url))continue;
  let result:{status:string;headline:string|null;description:string|null;publishedAt:string|null;hash:string|null;error:string|null};
  try{
   const response=await request(url,{redirect:"error",signal:AbortSignal.timeout(8000),headers:{Accept:"text/html"}});
   if(!response.ok||!response.headers.get("content-type")?.includes("text/html"))throw new Error("source_unavailable");
   const html=await readBoundedText(response,2_000_000);
   const metadata=publisherMetadata(html,now);
   if(!metadata.headline&&!metadata.description)throw new Error("metadata_missing");
   const bytes=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(html));
   const hash=[...new Uint8Array(bytes)].map(b=>b.toString(16).padStart(2,"0")).join("");
   result={status:"READ",...metadata,hash,error:null};
  }catch(error){
   result={status:"FAILED",headline:null,description:null,publishedAt:null,hash:null,error:error instanceof Error&&error.message==="metadata_missing"?"metadata_missing":"source_unavailable"};
  }
  await db.prepare(`INSERT OR IGNORE INTO catalyst_investigations(source_url,observed_at,status,headline,description,published_at,payload_sha256,error_code)
   VALUES (?,?,?,?,?,?,?,?)`).bind(url,stamp,result.status,result.headline,result.description,result.publishedAt,result.hash,result.error).run();
 }
}
