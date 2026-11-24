// Accept only a single identifiable Product with a single explicit Offer.
export function productOffer(html){
 const products=[];
 for(const m of html.matchAll(/<script\b[^>]*type\s*=\s*["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi)){
  try{
   const visit=x=>{if(Array.isArray(x)){x.forEach(visit);return;}if(!x||typeof x!=="object")return;if(x["@type"]==="Product"||Array.isArray(x["@type"])&&x["@type"].includes("Product"))products.push(x);if(x["@graph"])visit(x["@graph"]);};
   visit(JSON.parse(m[1]));
  }catch{}
 }
 if(products.length!==1)return null;
 const p=products[0],o=Array.isArray(p.offers)?(p.offers.length===1?p.offers[0]:null):p.offers;
 if(typeof p.name!=="string"||!p.name.trim())return null;
 const offer=o&&o["@type"]==="Offer"?o:null;
 const price=offer?.price, currency=offer?.priceCurrency;
 const cents=typeof price==="number"||typeof price==="string"&&/^\d+(?:\.\d{1,2})?$/.test(price)?Math.round(Number(price)*100):null;
 const valid=Number.isSafeInteger(cents)&&cents>0&&typeof currency==="string"&&/^[A-Z]{3}$/.test(currency);
 const availability=typeof offer?.availability==="string"?offer.availability.replace(/^https?:\/\/schema\.org\//,""):"";
 return {name:p.name.trim().slice(0,300),sku:typeof p.sku==="string"?p.sku.slice(0,100):null,priceCents:valid?cents:null,currency:valid?currency:null,availability:["InStock","OutOfStock","PreOrder","BackOrder","SoldOut","LimitedAvailability"].includes(availability)?availability:"UNKNOWN"};
}
