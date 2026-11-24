// Extract only text-bearing, same-publisher article links; no guessed dates or product IDs.
export function wizardArticles(html) {
 const found=new Map();
 for(const match of html.matchAll(/<a\b[^>]*\bhref\s*=\s*["']([^"']+)["'][^>]*>([\s\S]*?)<\/a\s*>/gi)){
  try{
   const u=new URL(match[1],"https://magic.wizards.com");
   if(u.protocol!=="https:"||!["magic.wizards.com","www.magic.wizards.com"].includes(u.hostname)||u.username||u.password||!/^\/en\/news\/(?:announcements|feature)\/[a-z0-9-]+\/?$/.test(u.pathname))continue;
   u.hostname="magic.wizards.com";u.search="";u.hash="";u.pathname=u.pathname.replace(/\/$/,"");
   const title=match[2].replace(/<[^>]*>/g," ").replace(/&amp;/g,"&").replace(/&quot;/g,'"').replace(/&#39;|&apos;/g,"'").replace(/&nbsp;/g," ").replace(/\s+/g," ").trim();
   if(title.length<12||title.length>300||/^(?:learn more|read more|see the cards)/i.test(title))continue;
   if(!found.has(u.href))found.set(u.href,{url:u.href,title});
  }catch{}
 }
 return [...found.values()].slice(0,40);
}
