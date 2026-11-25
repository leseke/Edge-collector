"use client";
import {useState,useId} from "react";
import type {SaleVariant} from "../lib/radar-paid-sales";
const horizons=[7,30,90,365,0] as const;
const money=new Intl.NumberFormat("fr-FR",{style:"currency",currency:"EUR"});
const dayLabel=new Intl.DateTimeFormat("fr-FR",{day:"numeric",month:"short",year:"2-digit",timeZone:"UTC"});
export function ProductSalesHistory({variants,asOf,archiveOnly=false}:{variants:SaleVariant[];asOf:string;archiveOnly?:boolean}){
 const [key,setKey]=useState(variants[0]?.key??"");
 const [days,setDays]=useState<number>(365);
 const id=useId();
 const variant=variants.find(v=>v.key===key)??variants[0];
 const today=Date.parse(asOf+"T00:00:00Z");
 const sales=[...new Map((variant?.paidSales??[]).filter(s=>/^\d{4}-\d{2}-\d{2}$/.test(s.day)&&Number.isSafeInteger(s.cents)&&s.cents>0&&Date.parse(s.day)<=today&&(!days||Date.parse(s.day)>=today-(days-1)*86400000)).map(s=>[s.id,s])).values()].sort((a,b)=>a.day.localeCompare(b.day)||a.id.localeCompare(b.id));
 const prices=sales.map(s=>s.cents).sort((a,b)=>a-b),n=prices.length;
 const median=n?(prices[Math.floor((n-1)/2)]+prices[Math.floor(n/2)])/2:null;
 const dates=sales.map(s=>Date.parse(s.day));
 const x0=dates[0]??0,x1=dates.at(-1)??x0;
 const lo=prices[0]??0,hi=prices.at(-1)??lo,pad=Math.max((hi-lo)*.12,hi*.03,1);
 const y0=Math.max(0,lo-pad),y1=hi+pad;
 const x=(d:number)=>x1===x0?180:24+(d-x0)/(x1-x0)*312;
 const y=(p:number)=>144-(p-y0)/(y1-y0)*120;
 return <section className="edge-financial-history" aria-labelledby={id}>
 <header><div><p className="native-eyebrow">TRANSACTIONS PAYÉES</p><h2 id={id}>Historique des ventes</h2></div><span className="edge-history-source">GCC{archiveOnly?" · Archive":""}</span></header>
 {!variant?<p className="edge-history-empty">Aucun historique de ventes associé à cette référence. Aucun graphique estimé.</p>:<>
 <label className="edge-history-variant">Variante observée<select value={variant.key} onChange={e=>setKey(e.target.value)}>{variants.map(v=><option key={v.key} value={v.key}>{v.variant}</option>)}</select></label>
 <div className="edge-history-horizons" role="group" aria-label="Période de consultation">{horizons.map(h=><button key={h} type="button" aria-pressed={days===h} onClick={()=>setDays(h)}>{h===0?"Tout":h===365?"1 an":h+" j"}</button>)}</div>
 <div className="edge-history-metrics"><div><span>Dernière vente de la période</span><strong>{n?money.format(sales[n-1].cents/100):"—"}</strong></div><div><span>Médiane</span><strong>{median===null?"—":money.format(median/100)}</strong></div><div><span>Transactions</span><strong>{n}</strong></div></div>
 {n>0?<><div className="edge-history-chart"><svg viewBox="0 0 360 170" role="img" aria-label={n+" transactions payées, minimum "+money.format(lo/100)+", maximum "+money.format(hi/100)}>
 {[0,.5,1].map(t=><line key={t} x1="24" x2="336" y1={24+t*120} y2={24+t*120} stroke="#263448" strokeDasharray="4 5"/>)}
 {sales.map((s,i)=><circle key={s.id} cx={x(dates[i])} cy={y(s.cents)} r="4" fill="#4e83f5" stroke="#e1ebff" strokeWidth="1"><title>{dayLabel.format(new Date(s.day))} · {money.format(s.cents/100)}</title></circle>)}
 </svg><div className="edge-history-axis"><span>{dayLabel.format(new Date(x0))}</span><span>{money.format(lo/100)} – {money.format(hi/100)}</span><span>{dayLabel.format(new Date(x1))}</span></div></div>
 <details className="edge-history-sales"><summary>Voir les transactions ({n})</summary><ul>{[...sales].reverse().map(s=><li key={s.id}><a href={s.source} target="_blank" rel="noopener noreferrer">{dayLabel.format(new Date(s.day))} · GCC ↗</a><strong>{money.format(s.cents/100)}</strong></li>)}</ul></details></>:<p className="edge-history-empty">Aucune vente payée observée dans cette période.</p>}
 <p className="edge-history-note">Chaque point représente une transaction documentée. Pas d’interpolation, ni de mélange des grades ou langues. « Tout » désigne l’historique disponible dans EDGE, non l’intégralité du marché.</p>
 </>}
 </section>;
}
