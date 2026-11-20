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
export function verifiedSaleVariantForListing(title,keys){
  const description=normalize(title);
  if(!description||description.length>500||!Array.isArray(keys))return null;
  const matches=[];
  for(const key of keys.slice(0,1000)){
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
  return matches.length===1?matches[0]:null;
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
export function comparablePaidSales(title,sales,now=Date.now()){
  if(!Array.isArray(sales))return {status:"NO_VERIFIED_VARIANT"};
  const key=verifiedSaleVariantForListing(title,sales.map(s=>s?.variant_key));
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
