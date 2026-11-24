import {wizardArticles} from "./catalyst-parser.mjs";
import {readBoundedText} from "./bounded.mjs";
export async function collectCatalysts(db:D1Database,request=fetch,now=new Date()){
 const publisher="Wizards of the Coast",stamp=now.toISOString(),id=crypto.randomUUID();
 try{
  const response=await request("https://magic.wizards.com/en/news",{redirect:"error",signal:AbortSignal.timeout(8000),headers:{Accept:"text/html"}});
  if(!response.ok||!response.headers.get("content-type")?.includes("text/html"))throw new Error("source_unavailable");
  const html=await readBoundedText(response,2_000_000);
  const articles=wizardArticles(html);
  if(!articles.length)throw new Error("no_parseable_articles");
  const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(html));
  const hash=[...new Uint8Array(digest)].map(b=>b.toString(16).padStart(2,"0")).join("");
  const result=await db.batch([
   db.prepare(`INSERT OR IGNORE INTO catalyst_discoveries(source_url,publisher,title,first_seen_at,payload_sha256)
    SELECT json_extract(value,'$.url'),?,json_extract(value,'$.title'),?,? FROM json_each(?)`).bind(publisher,stamp,hash,JSON.stringify(articles)),
   db.prepare(`INSERT INTO catalyst_scan_runs(run_id,observed_at,publisher,status,discovered)
    VALUES (?,?,?,CASE WHEN changes()>0 THEN 'OK' ELSE 'EMPTY' END,changes())`).bind(id,stamp,publisher)
  ]);
  return {status:"COMPLETED",inserted:result[0].meta.changes??0};
 }catch{
  await db.prepare("INSERT INTO catalyst_scan_runs(run_id,observed_at,publisher,status,discovered) VALUES (?,?,?,'FAILED',0)").bind(id,stamp,publisher).run();
  return {status:"FAILED",inserted:0};
 }
}
