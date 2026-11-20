// Autonomous, bounded review queue from ACTUAL paid GCC ledger rows.
// A paid lot may indicate a catalog identity to investigate, not confirm it.
// Never mint an official product identifier, link or VERIFIED status.
import {parsePackagedVariantKey} from "./leboncoin-product-identities.mjs";
const DAY=86400000;
const canonicalLot=row=>typeof row?.lot_id==="string" &&
  /^gcc-[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(row.lot_id) &&
  row.source_url==="https://gradedcardcenter.com/item/"+row.lot_id.slice(4);
const dateValue=value=>{
  if(typeof value!=="string"||!/^(\d{4})-(\d{2})-(\d{2})$/.test(value))return NaN;
  const parsed=Date.parse(value+"T00:00:00Z");
  return Number.isFinite(parsed)&&new Date(parsed).toISOString().slice(0,10)===value
    ?parsed:NaN;
};
export function discoverPackagedCandidates(rows,{
  now=Date.now(),maxRows=1000,maxCandidates=12
}={}){
  if(!Array.isArray(rows)||rows.length>maxRows||!Number.isFinite(now)||
     !Number.isInteger(maxCandidates)||maxCandidates<1||maxCandidates>50)
    return {status:"SOURCE_UNAVAILABLE_OR_INCOMPLETE",candidates:[]};
  const groups=new Map(),cutoff=now-365*DAY;
  for(const row of rows){
    const spec=parsePackagedVariantKey(row?.variant_key);
    const soldAt=dateValue(row?.sold_day);
    if(!spec||!canonicalLot(row)||!Number.isSafeInteger(row.price_cents)||
       row.price_cents<=0||!Number.isFinite(soldAt)||soldAt>now||
       soldAt<cutoff)continue;
    const key=row.variant_key;
    if(!groups.has(key))groups.set(key,{key,spec,lots:new Map(),newestDay:""});
    const group=groups.get(key);
    if(!group.lots.has(row.lot_id)){
      group.lots.set(row.lot_id,row.price_cents);
      if(row.sold_day>group.newestDay)group.newestDay=row.sold_day;
    }
  }
  const candidates=[...groups.values()].map(group=>({
    status:"CANDIDATE_UNVERIFIED",
    variantKey:group.key,
    packaging:group.spec.type,
    series:group.spec.series,
    product:group.spec.product,
    language:group.spec.language,
    edition:group.spec.printing,
    units:group.spec.units,
    paidLotCount:group.lots.size,
    latestPaidDay:group.newestDay,
    missingEvidence:["OFFICIAL_PRODUCT_REFERENCE","PACKAGING_AND_LOCALE_VERIFICATION",
      "REVIEWED_IDENTIFIERS","MATCHING_LISTING_ATTRIBUTES"]
  })).sort((a,b)=>b.paidLotCount-a.paidLotCount ||
      b.latestPaidDay.localeCompare(a.latestPaidDay) ||
      a.variantKey.localeCompare(b.variantKey)).slice(0,maxCandidates);
  return {status:candidates.length?"CANDIDATES_FOUND":"NO_CANDIDATES",candidates};
}
