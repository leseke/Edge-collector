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

export function philibertCandidates(html){
 const found=new Map();
 for(const m of html.matchAll(/<a\b[^>]*\bhref\s*=\s*["']([^"']+)["'][^>]*>([\s\S]*?)<\/a\s*>/gi)){
  try{
   const u=new URL(m[1],"https://www.philibertnet.com");
   if(u.protocol!=="https:"||u.hostname!=="www.philibertnet.com"||u.username||u.password||!/^\/fr\/[a-z0-9-]+\/\d+-[a-z0-9-]+-\d{8,14}\.html$/.test(u.pathname))continue;
   u.search="";u.hash="";
   const title=m[2].replace(/<[^>]*>/g," ").replace(/&amp;/g,"&").replace(/&nbsp;/g," ").replace(/\s+/g," ").trim();
   if(title.length<12||title.length>300)continue;
   if(!found.has(u.href))found.set(u.href,{url:u.href,title});
  }catch{}
 }
 return [...found.values()].slice(0,100);
}
export const merchantSources=[
 {merchant:"Playin",catalog:"https://www.play-in.com/fr/gamme/1/magic/catalogue",parse:playinCandidates,product:/^https:\/\/www\.play-in\.com\/fr\/produit\/\d+\/[a-z0-9-]+\/?$/},
 {merchant:"Philibert",catalog:"https://www.philibertnet.com/fr/120-magic-l-assemblee",parse:philibertCandidates,product:/^https:\/\/www\.philibertnet\.com\/fr\/[a-z0-9-]+\/\d+-[a-z0-9-]+-\d{8,14}\.html$/}
];
export function exactGtin(value){
 if(typeof value!=="string"||!/^\d+$/.test(value)||![8,12,13,14].includes(value.length))return null;
 let sum=0;
 for(let i=value.length-2,weight=3;i>=0;i--,weight=4-weight)sum+=Number(value[i])*weight;
 if((10-sum%10)%10!==Number(value.at(-1)))return null;
 return value.padStart(14,"0");
}
export function comparableOffers(rows){
 const groups=new Map();
 for(const row of rows){
  const gtin=exactGtin(row.gtin);
  if(!gtin||!row.fresh||row.status!=="READ"||row.currency!=="EUR"||!Number.isSafeInteger(row.priceCents)||row.priceCents<=0||!["InStock","PreOrder"].includes(row.availability))continue;
  const key=gtin+"|"+row.availability;
  const group=groups.get(key)??[];
  if(!group.some(x=>x.merchant===row.merchant))group.push(row);
  groups.set(key,group);
 }
 return [...groups.entries()].filter(([,g])=>g.length>=2).map(([key,g])=>({key,offers:g.sort((a,b)=>a.priceCents-b.priceCents),spreadCents:Math.max(...g.map(x=>x.priceCents))-Math.min(...g.map(x=>x.priceCents))}));
}
