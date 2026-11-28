import type { Signal } from "./nervous-system";
export type Observation = { id:string; source:string; listingId:string; subject:string; observedAt:number; priceMinor:number|null; currency:string; language:string; condition:string; url:string; priceKind:"asking"|"sold"|"auction" };
export type Reference = { subject:string; currency:string; language:string; condition:string; priceKind:Observation["priceKind"]; medianMinor:number; sampleSize:number };
export type Verdict = { status:"accepted"|"review"|"rejected"|"duplicate"; reasons:string[]; signal:Signal|null };
export function inspect(o:Observation, previous:readonly Observation[], refs:readonly Reference[], now:number, ttl:number):Verdict {
 if (!Number.isSafeInteger(now)||!Number.isSafeInteger(ttl)||ttl<=0||!Number.isSafeInteger(now+ttl)) throw new Error("invalid clock");
 const reasons:string[]=[];
 if (![o.id,o.source,o.listingId,o.subject,o.currency,o.language,o.condition].every(v=>typeof v==="string"&&v.trim().length>0)) reasons.push("missing_identity");
 if (!Number.isSafeInteger(o.observedAt)||o.observedAt<0||o.observedAt>now) reasons.push("invalid_timestamp");
 if (!/^[A-Z]{3}$/.test(o.currency)) reasons.push("invalid_currency");
 if (!["asking","sold","auction"].includes(o.priceKind)) reasons.push("invalid_price_kind");
 if (o.priceMinor!==null&&(!Number.isSafeInteger(o.priceMinor)||o.priceMinor<=0)) reasons.push("invalid_price");
 try { if (new URL(o.url).protocol!=="https:") reasons.push("invalid_url"); } catch { reasons.push("invalid_url"); }
 const finish=(status:Verdict["status"],why:string[]):Verdict=>({status,reasons:why,signal:status==="rejected"&&o.id&&o.subject?{id:JSON.stringify([o.id,"rejected"]),kind:"evidence.rejected",subject:o.subject,observedAt:now,expiresAt:now+ttl}:null});
 if(reasons.length) return finish("rejected",reasons);
 if(previous.some(p=>p.source===o.source&&p.listingId===o.listingId&&p.observedAt===o.observedAt&&p.priceMinor===o.priceMinor&&p.currency===o.currency&&p.subject===o.subject&&p.language===o.language&&p.condition===o.condition&&p.priceKind===o.priceKind)) return finish("duplicate",["identical_observation"]);
 if(previous.some(p=>p.source===o.source&&p.listingId===o.listingId&&p.observedAt===o.observedAt)) reasons.push("conflicting_observation");
 if(o.priceMinor===null) reasons.push("missing_price");
 else for(const r of refs) {
  if(r.subject!==o.subject||r.currency!==o.currency||r.language!==o.language||r.condition!==o.condition||r.priceKind!==o.priceKind||!Number.isSafeInteger(r.sampleSize)||r.sampleSize<5||!Number.isSafeInteger(r.medianMinor)||r.medianMinor<=0) continue;
  const ratio=o.priceMinor/r.medianMinor;
  if(ratio<0.25||ratio>4) {reasons.push("price_outlier");break;}
 }
 // Structural acceptance is NOT independent verification of a sale or listing.
 return finish(reasons.length?"review":"accepted",reasons);
}
