// Versioned and review-gated product identity catalogue for packaged collectibles.
// Deliberately EMPTY in production until official references and actual GCC
// variant keys are verified; sample entries exist exclusively in tests.
// This is not user-maintained data, and never infers a product from an ad title.
export const PRODUCT_IDENTITY_SCHEMA_VERSION=1;
export const reviewedPackagedProducts=Object.freeze([]);

const slug=/^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const allowedTypes=new Set(["etb","upc","display","coffret"]);
const languages={
  fr:["fr","francais","french"],en:["en","anglais","english"],
  ja:["ja","jp","japonais","japanese"],de:["de","allemand","german"],
  es:["es","espagnol","spanish"],it:["it","italien","italian"]
};
const clean=v=>typeof v==="string"?v.normalize("NFKD")
  .replace(/[\u0300-\u036f]/g,"").toLowerCase()
  .replace(/[^a-z0-9]+/g," ").trim():"";
const phrase=(text,needle)=>Boolean(needle)&&(" "+text+" ").includes(" "+needle+" ");
const sealed=title=>["scelle","sealed","non ouvert","sous blister"]
  .some(term=>phrase(title,term));
function unpack(key){
  // Eight fields: kind:pokemon:set:product:lang:printing:units:scelle.
  if(typeof key!=="string"||key.length>240)return null;
  const parts=key.split(":");
  if(parts.length!==8||!allowedTypes.has(parts[0])||parts[1]!=="pokemon"||
     parts[7]!=="scelle"||!slug.test(parts[2])||!slug.test(parts[3])||
     !Object.hasOwn(languages,parts[4])||
     !["unlimited","first-edition"].includes(parts[5])||
     !/^u(?:[1-9]|[1-9][0-9]{1,2})$/.test(parts[6]))return null;
  return {type:parts[0],series:parts[2],product:parts[3],
    language:parts[4],printing:parts[5],units:Number(parts[6].slice(1))};
}
const categoryLabels={
  etb:["etb","elite trainer box","boite dresseur d elite"],
  upc:["upc","ultra premium collection","collection ultra premium"],
  display:["display","boite de 36 boosters","booster box"],
  coffret:["coffret","collection box"]
};
const forbiddenFor={
  etb:["upc","ultra premium","display","booster unitaire","lot de","bundle"],
  upc:["etb","elite trainer","display","booster unitaire","lot de","bundle"],
  display:["etb","upc","ultra premium","booster unitaire","lot de","bundle"],
  coffret:["etb","upc","ultra premium","display","booster unitaire","lot de","bundle"]
};
function validEntry(entry){
  if(!entry||entry.version!==PRODUCT_IDENTITY_SCHEMA_VERSION||
     entry.reviewStatus!=="VERIFIED"||!unpack(entry.variantKey)||
     !Array.isArray(entry.identifiers)||entry.identifiers.length<2||
     entry.identifiers.length>8||entry.identifiers.some(x=>
       typeof x!=="string"||clean(x).length<4||clean(x).length>100)||
     new Set(entry.identifiers.map(clean)).size!==entry.identifiers.length||
     typeof entry.verifiedOn!=="string"||
     !/^\d{4}-\d\d-\d\d$/.test(entry.verifiedOn)||
     Number.isNaN(Date.parse(entry.verifiedOn+"T00:00:00Z")))return false;
  try{
    const url=new URL(entry.officialSource);
    if(url.protocol!=="https:"||url.username||url.password||url.port||
       url.hash||url.search||
       !["pokemon.com","www.pokemon.com","corporate.pokemon.co.jp",
         "www.pokemoncenter.com"].includes(url.hostname))return false;
  }catch{return false}
  return true;
}
export function catalogVariantForListing(title,variants,catalog=reviewedPackagedProducts){
  const text=clean(title);
  if(!text||text.length>500||!Array.isArray(variants)||
     !Array.isArray(catalog)||catalog.length>1000)return null;
  const keys=new Set(variants.filter(x=>typeof x==="string"));
  const hits=[];
  for(const entry of catalog){
    if(!validEntry(entry)||!keys.has(entry.variantKey))continue;
    const v=unpack(entry.variantKey);
    if(!sealed(text)||!categoryLabels[v.type].some(x=>phrase(text,x))||
       forbiddenFor[v.type].some(x=>phrase(text,x)))continue;
    if(!phrase(text,clean(v.series.replaceAll("-"," ")))||
       !phrase(text,clean(v.product.replaceAll("-"," ")))||
       !languages[v.language].some(x=>phrase(text,x))||
       !(v.printing==="unlimited"
         ?["unlimited","sans edition"].some(x=>phrase(text,x))
         :["1ere edition","first edition","1st edition"].some(x=>phrase(text,x))))
      continue;
    // Specific exact product identifiers; never character names alone.
    if(!entry.identifiers.every(x=>phrase(text,clean(x))))continue;
    if(v.units===1){
      if(!["1 unite","unitaire","1 coffret","1 display","1 etb","1 upc",
           "1 boite","une boite"].some(x=>phrase(text,x)))continue;
    }else{
      if(!phrase(text,v.units+" unites"))continue;
    }
    hits.push(entry.variantKey);
    if(hits.length>1)return null;
  }
  return hits.length===1?hits[0]:null;
}
