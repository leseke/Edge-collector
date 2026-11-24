import {getMarketPatterns} from "../lib/market-patterns";
import type {SaleVariant} from "../lib/radar-paid-sales";
const euros=new Intl.NumberFormat("fr-FR",{style:"currency",currency:"EUR"});
export async function MarketPatternPanel({variants}:{variants:SaleVariant[]}){
 const report=await getMarketPatterns();
 return <section className="dashboard-section radar-section" aria-labelledby="pattern-title">
 <h2 id="pattern-title">Configurations précurseurs</h2>
 <p>Accélération des ventes payées relevées sans hausse significative du prix médian. Hypothèse à investiguer, pas une prévision.</p>
 {report===null?<p>Analyse momentanément indisponible.</p>:report.partial?<p>Échantillon tronqué : aucune classification fiable.</p>:report.items.length===0?<p>Aucune configuration répondant aux critères dans les relevés disponibles.</p>:report.items.map(p=>{
 const v=variants.find(v=>v.key===p.variant);
 return <article className="edge-mri-case" key={p.variant}>
 <small>SIGNAL EXPLORATOIRE · À INVESTIGUER</small>
 <h3>{v?.name??p.variant}</h3>
 {v&&<p>{v.variant}</p>}
 <p>{p.priorCount} puis {p.recentCount} ventes relevées sur deux périodes de 14 jours.</p>
 <p>Médianes : {euros.format(p.before/100)} → {euros.format(p.after/100)} ({p.change.toFixed(1)} %).</p>
 <p>Hypothèse : intérêt croissant sans revalorisation observée. Vérifier la couverture, les remises en vente et les catalyseurs.</p>
 <details className="radar-disclosure"><summary>Transactions récentes documentées</summary><ul>{p.evidence.map(s=><li key={s.lot_id}><a href={"https://gradedcardcenter.com/item/"+s.lot_id.slice(4)} target="_blank" rel="noopener noreferrer">{s.sold_day} · {euros.format(s.price_cents/100)} ↗</a></li>)}</ul></details>
 </article>;
 })}
 <p className="radar-sales-description">Critères exploratoires : au moins 3 puis 5 ventes relevées, hausse du volume d’au moins 50 %, médiane dans ±5 %. La couverture historique peut être incomplète ; les volumes relevés ne représentent pas nécessairement le marché entier.</p>
 </section>;
}
