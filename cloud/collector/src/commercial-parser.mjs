// Candidate links only. No product identity, price or stock inferred from anchor text.
export function playinCandidates(html){
 const items=new Map();
 for(const m of html.matchAll(/<a\b[^>]*\bhref\s*=\s*["']([^"']+)["'][^>]*>([\s\S]*?)<\/a\s*>/gi)){
  try{
   const u=new URL(m[1],"https://www.play-in.com");
   if(u.protocol!=="https:"||u.hostname!=="www.play-in.com"||u.username||u.password||!/^\/fr\/produit\/[^/]+(?:\/[^/]+)?\/?$/.test(u.pathname))continue;
   u.search="";u.hash="";
   const title=m[2].replace(/<[^>]*>/g," ").replace(/&amp;/g,"&").replace(/&nbsp;/g," ").replace(/\s+/g," ").trim();
   if(title.length<12||title.length>300)continue;
   if(!items.has(u.href))items.set(u.href,{url:u.href,title});
  }catch{}
 }
 return [...items.values()].slice(0,100);
}
export function normalizeResearchText(text){return text.normalize("NFD").replace(/\p{Diacritic}/gu,"").toLowerCase().replace(/[^a-z0-9]+/g," ").trim();}
export function candidateMatches(headline,items){
 const stop=new Set(["magic","gathering","the","and","with","new","collection","cards","card","release","announced","announcement","booster","deck","display","collector","edition","francais","anglais","produit","bundle"]);
 const tokens=new Set(normalizeResearchText(headline).split(" ").filter(t=>t.length>=4&&!stop.has(t)));
 return items.map(item=>({...item,overlap:[...new Set(normalizeResearchText(item.title).split(" "))].filter(t=>tokens.has(t))})).filter(item=>item.overlap.length>=2).sort((a,b)=>b.overlap.length-a.overlap.length||a.url.localeCompare(b.url)).slice(0,5);
}
