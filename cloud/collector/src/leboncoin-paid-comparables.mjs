import {catalogVariantForListing,reviewedPackagedProducts} from "./leboncoin-product-identities.mjs";
// Strict provenance-aware joins of email listings to GCC paid-sale variants.
// No fuzzy matching. Any missing variant attribute means NO_COMPARABLE.
const normalize=value=>typeof value==="string"
  ?value.normalize("NFKD").replace(/[\u0300-\u036f]/g,"").toLowerCase()
    .replace(/[^a-z0-9.]+/g," ").trim():"";
const includesPhrase=(haystack,phrase)=>Boolean(phrase)&&
  (" "+haystack+" ").includes(" "+phrase+" ");
const languages={
  fr:["fr","francais","french"],en:["en","anglais","english"],
  jp:["jp","japonais","japanese"],ja:["ja","japonais","japanese"],
  de:["de","allemand","german"],es:["es","espagnol","spanish"],
  it:["it","italien","italian"]
};
function canonicalVariant(key){
  if(typeof key!=="string"||key.length>240)return null;
  const parts=key.split(":");
  if(parts.length!==9||parts[0]!=="carte"||parts[1]!=="pokemon")return null;
  const [, , set,number,name,language,printing,grader,score]=parts;
  if(!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(set)||
     !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(name)||
     !/^[0-9]{1,4}(?:-[0-9]{1,4})?$/.test(number)||
     !languages[language]||
     !["unlimited","first-edition"].includes(printing)||
     !["psa","pca","bgs","cgc"].includes(grader)||
     !/^(?:[1-9]|10)(?:\.5)?$/.test(score))return null;
  return {set,number,name,language,printing,grader,score};
}
// A sealed identity has exactly seven fields in the existing GCC ledger:
// booster|coffret:pokemon:set:product-name:language:printing:scelle.
// Only explicit single-booster or named-box labels qualify; mixed lots,
// displays and bundles are not equated to a single sealed product.
function sealedVariant(key){
  if(typeof key!=="string"||key.length>240)return null;
  const p=key.split(":");
  if(p.length!==7||!["booster","coffret"].includes(p[0])||
     p[1]!=="pokemon"||p[6]!=="scelle")return null;
  const [, ,set,name,language,printing]=p;
  if(!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(set)||
     !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(name)||
     !languages[language]||
     !["unlimited","first-edition"].includes(printing))return null;
  return {type:p[0],set,name,language,printing};
}
const sealedTerm=d=>["scelle","sealed","non ouvert","sous blister"].some(v=>includesPhrase(d,v));
const printingTerm=(d,p)=>p==="unlimited"
  ?includesPhrase(d,"unlimited")||includesPhrase(d,"sans edition")
  :["1ere edition","first edition","1st edition"].some(v=>includesPhrase(d,v));
const sealedMatch=(description,v)=>{
  if(!includesPhrase(description,v.set.replaceAll("-"," "))||
     !includesPhrase(description,v.name.replaceAll("-"," "))||
     !languages[v.language].some(x=>includesPhrase(description,x))||
     !printingTerm(description,v.printing)||!sealedTerm(description))return false;
  // A plain word "booster" is not proof that this is one single booster.
  if(v.type==="booster"){
    if(!includesPhrase(description,"booster unitaire") &&
       !includesPhrase(description,"1 booster") &&
       !includesPhrase(description,"booster individuel"))return false;
    if(["display","booster box","lot","bundle","pack de","coffret","etb",
         "x 2","x 3","x 4","x 6","x 10","x 12","x 24","x 36"]
         .some(v=>includesPhrase(description,v)))return false;
  }else{
    if(!includesPhrase(description,"coffret") ||
       ["lot de coffrets","lot de","bundle","display","booster unitaire"]
         .some(v=>includesPhrase(description,v)))return false;
  }
  return true;
};
export function verifiedSaleVariantForListing(title,keys,catalog=reviewedPackagedProducts){
  const description=normalize(title);
  if(!description||description.length>500||!Array.isArray(keys))return null;
  const matches=[];
  for(const key of new Set(keys.slice(0,1000))){
    const sealed=sealedVariant(key);
    if(sealed){
      if(sealedMatch(description,sealed)){
        matches.push(key);
        if(matches.length>1)return null;
      }
      continue;
    }
    const v=canonicalVariant(key);
    if(!v)continue;
    const cardNumber=v.number.replace("-","/");
    const localizedNumber=cardNumber.replace("/"," ");
    if(!includesPhrase(description,v.set.replaceAll("-"," "))||
       !includesPhrase(description,v.name.replaceAll("-"," "))||
       !(includesPhrase(description,cardNumber)||includesPhrase(description,localizedNumber))||
       !languages[v.language].some(x=>includesPhrase(description,x))||
       !includesPhrase(description,v.grader+" "+v.score)||
       !(v.printing==="unlimited"
         ?includesPhrase(description,"unlimited")||includesPhrase(description,"sans edition")
         :includesPhrase(description,"1ere edition")||includesPhrase(description,"first edition")||includesPhrase(description,"1st edition")))
      continue;
    matches.push(key);
    if(matches.length>1)return null;
  }
  const packaged=catalogVariantForListing(title,keys,catalog);
  if(packaged && matches.length)return null;
  return matches.length===1?matches[0]:packaged;
}
const safeSale=row=>{
  if(!row||typeof row.variant_key!=="string"||
     typeof row.lot_id!=="string"||typeof row.sold_day!=="string"||
     !Number.isSafeInteger(row.price_cents)||row.price_cents<=0||
     !/^gcc-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(row.lot_id)||
     row.source_url!=="https://gradedcardcenter.com/item/"+row.lot_id.slice(4)||
     !/^\d{4}-\d\d-\d\d$/.test(row.sold_day)||
     !Number.isFinite(Date.parse(row.sold_day+"T00:00:00Z")))return false;
  return true;
};
export function comparablePaidSales(title,sales,now=Date.now(),catalog=reviewedPackagedProducts){
  if(!Array.isArray(sales))return {status:"NO_VERIFIED_VARIANT"};
  const key=verifiedSaleVariantForListing(title,sales.map(s=>s?.variant_key),catalog);
  if(!key)return {status:"NO_VERIFIED_VARIANT"};
  const asOf=new Date(now).toISOString().slice(0,10);
  const cutoff=now-90*86400000;
  const unique=new Map();
  for(const sale of sales){
    if(!safeSale(sale)||sale.variant_key!==key||sale.sold_day>asOf||
       Date.parse(sale.sold_day+"T00:00:00Z")<cutoff)continue;
    unique.set(sale.lot_id,sale);
  }
  if(unique.size<3)return {status:"INSUFFICIENT_PAID_SALES"};
  const prices=[...unique.values()].map(s=>s.price_cents).sort((a,b)=>a-b);
  const mid=Math.floor(prices.length/2);
  const median=prices.length%2?prices[mid]:Math.floor((prices[mid-1]+prices[mid])/2);
  return {status:"COMPARABLE",variant:key,saleCount:prices.length,
    medianCents:median,lowCents:prices[0]};
}
