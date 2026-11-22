// Deterministic lead triage. Never infer market value from email snippets.
// Output is an investigation cue, not BUY, a verified stock flag or realized P/L.
const cents=n=>Number.isSafeInteger(n)&&n>=0&&n<=1_000_000_000;
const hits=n=>Number.isSafeInteger(n)&&n>=1&&n<=1_000_000;
export function scoreLeboncoinLead(row,now=Date.now()){
  const time=typeof row?.observed_at==="string"?Date.parse(row.observed_at):NaN;
  const ageHours=Number.isFinite(time)&&time<=now ? (now-time)/3_600_000:Infinity;
  const recent=ageHours<=48;
  const count=hits(row?.alert_hits)?row.alert_hits:1;
  const from=cents(row?.first_price_cents)?row.first_price_cents:null;
  const to=cents(row?.price_cents)?row.price_cents:null;
  if(count>=2 && from!==null && from>0 && to!==null && to<from){
    const drop=from-to, percent=(drop/from)*100;
    // Avoid mistaking tiny rounding changes for an actionable signal.
    if(recent && drop>=500 && percent>=5)
      return {kind:"PRICE_DROP",rank:0,changeCents:-drop,changePercent:percent,
        label:"Baisse du prix demandé à examiner"};
  }
  if(count>=2 && recent)return {kind:"REPEATED",rank:1,changeCents:null,
    changePercent:null,label:"Annonce réapparue dans les alertes"};
  return {kind:"OBSERVED",rank:2,changeCents:null,changePercent:null,
    label:recent?"Nouvelle observation":"Observation ancienne"};
}
export function sortLeboncoinLeads(rows,now=Date.now()){
  return [...rows].sort((left,right)=>{
    const a=scoreLeboncoinLead(left,now),b=scoreLeboncoinLead(right,now);
    if(a.rank!==b.rank)return a.rank-b.rank;
    if(a.kind==="PRICE_DROP" && b.kind==="PRICE_DROP" &&
      a.changePercent!==b.changePercent)return b.changePercent-a.changePercent;
    const ta=Date.parse(left.observed_at),tb=Date.parse(right.observed_at);
    if(Number.isFinite(ta)&&Number.isFinite(tb)&&ta!==tb)return tb-ta;
    return String(left.listing_id).localeCompare(String(right.listing_id));
  });
}
