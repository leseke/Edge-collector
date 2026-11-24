import type {ReactionCaseSummary} from "./market-data";
export type CatalystKind="REPRINT"|"EXCLUSIVITY"|"ANNIVERSARY"|"COLLABORATION"|"RELEASE"|"OTHER";
export function classifyCatalyst(title:string):CatalystKind{
 const t=title.normalize("NFD").replace(/\p{Diacritic}/gu,"").toLowerCase();
 if(/\b(reprint|reprints|reimpression|reassort|restock)\b/.test(t))return "REPRINT";
 if(/\b(exclusif|exclusive|exclusivity|exclusivite|limited edition|edition limitee)\b/.test(t))return "EXCLUSIVITY";
 if(/\b(anniversaire|anniversary)\b/.test(t))return "ANNIVERSARY";
 if(/\b(collaboration|crossover|partnership|partenariat)\b/.test(t))return "COLLABORATION";
 if(/\b(sortie|release|launch|lancement|preorder|precommande)\b/.test(t))return "RELEASE";
 return "OTHER";
}
export function catalystLeads(cases:ReactionCaseSummary[],now=new Date()){
 const seen=new Set<string>();
 return cases.flatMap(c=>c.publications.flatMap(p=>{
  try{
   const u=new URL(p.url);
   if(u.protocol!=="https:"||u.username||u.password||!p.title.trim())return [];
   u.hash="";const key=c.productId+"|"+u.href;
   if(seen.has(key))return [];seen.add(key);
   const stamp=Date.parse(p.publishedAt);
   const dated=Number.isFinite(stamp)&&stamp<=+now;
   return [{productId:c.productId,title:p.title,url:u.href,host:u.hostname,kind:classifyCatalyst(p.title),publishedAt:dated?new Date(stamp).toISOString():null,relationship:p.relationship,reactionStatus:c.reactionStatus}];
  }catch{return [];}
 })).sort((a,b)=>(b.publishedAt??"").localeCompare(a.publishedAt??"")||a.productId.localeCompare(b.productId)).slice(0,50);
}
