import type { recognizePatterns } from "./market-patterns";
import type { SupplyRow } from "./supply-patterns";
import type { AbsorptionRow } from "./market-absorption";
type Demand = ReturnType<typeof recognizePatterns>[number];
export function convergeSignals(demand:Demand[]|null,supply:SupplyRow[]|null,absorption:AbsorptionRow[]|null){
 const keys=new Set([...(demand??[]).map(x=>x.variant),...(supply??[]).map(x=>x.variant_key)]);
 return [...keys].map(key=>{
  const d=demand?.find(x=>x.variant===key)??null;
  const s=supply?.find(x=>x.variant_key===key)??null;
  const a=absorption?.find(x=>x.variant_key===key)??null;
  return {key,demand:d,supply:s,absorption:a,convergence:Boolean(d&&s),coverage:{demand:demand!==null,supply:supply!==null,absorption:absorption!==null}};
 }).sort((a,b)=>Number(b.convergence)-Number(a.convergence)||Number(Boolean(b.demand))-Number(Boolean(a.demand))||a.key.localeCompare(b.key));
}
