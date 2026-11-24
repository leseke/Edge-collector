// Article metadata is a publisher claim, not independent confirmation.
export function publisherMetadata(html,now=new Date()){
 const fields=new Map();
 const decode=s=>s.replace(/&amp;/g,"&").replace(/&quot;/g,'"').replace(/&#39;|&apos;/g,"'").replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/\s+/g," ").trim();
 for(const tag of html.matchAll(/<meta\b[^>]*>/gi)){
  const attrs=new Map(Array.from(tag[0].matchAll(/([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g),m=>[m[1].toLowerCase(),m[2]??m[3]]));
  const key=attrs.get("property")??attrs.get("name"),value=attrs.get("content");
  if(key&&value&&!fields.has(key))fields.set(key,decode(value));
 }
 const headline=fields.get("og:title")?.slice(0,300)||null;
 const description=(fields.get("og:description")??fields.get("description"))?.slice(0,1000)||null;
 const raw=fields.get("article:published_time");
 const stamp=typeof raw==="string"&&/^\d{4}-\d{2}-\d{2}(?:T.*)?$/.test(raw)?Date.parse(raw):NaN;
 return {headline,description,publishedAt:Number.isFinite(stamp)&&stamp<=+now?new Date(stamp).toISOString():null};
}
