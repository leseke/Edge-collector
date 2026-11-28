import {convergeSignals} from "../lib/signal-convergence";
import {getAbsorptionReport,absorptionRate} from "../lib/market-absorption";
import {getSupplyPatterns,supplyContraction} from "../lib/supply-patterns";
import {getMarketPatterns} from "../lib/market-patterns";
import type {SaleVariant} from "../lib/radar-paid-sales";
const euros=new Intl.NumberFormat("fr-FR",{style:"currency",currency:"EUR"});
export async function MarketPatternPanel({variants}:{variants:SaleVariant[]}){
 const [report,supply,absorption]=await Promise.all([getMarketPatterns(),getSupplyPatterns(),getAbsorptionReport()]);
 const combined=convergeSignals(report&&!report.partial?report.items:null,supply,absorption);
 const prioritized=combined.filter(c=>c.convergence);
 return <section className="dashboard-section radar-section" aria-labelledby="pattern-title">
 <h2 id="pattern-title">Configurations précurseurs</h2>
 <p>Accélération des ventes payées relevées sans hausse significative du prix médian. Hypothèse à investiguer, pas une prévision.</p>
 <div className="edge-scan-metrics"><div><span>Convergences détectées</span><strong>{report&&!report.partial&&supply!==null?prioritized.length:"—"}</strong></div><div><span>Signaux de ventes</span><strong>{report&&!report.partial?report.items.length:"—"}</strong></div><div><span>Signaux d’offre</span><strong>{supply?.length??"—"}</strong></div></div>
 <h3>Priorité · convergence des signaux</h3>
 {prioritized.length===0?<p>{report&&!report.partial&&supply!==null?"Aucune convergence dans les résultats consultés. Les signaux isolés restent des pistes.":"Données insuffisantes pour vérifier la convergence."}</p>:prioritized.slice(0,12).map(c=>{
 const v=variants.find(v=>v.key===c.key),d=c.demand!,s=c.supply!;
 return <article className="edge-mri-case" key={"convergence-"+c.key}>
 <small>PRÉCURSEUR · DEUX SIGNAUX CONCORDANTS</small><h3>{v?.name??s.title}</h3>{v&&<p>{v.variant}</p>}
 <div className="edge-scan-metrics"><div><span>Ventes relevées</span><strong>{d.priorCount} → {d.recentCount}</strong></div><div><span>Offres fixes</span><strong>{s.prior_count} → {s.current_count}</strong></div><div><span>Prix médian</span><strong>{d.change.toFixed(1)} %</strong></div></div>
 <p>Thèse à tester : hausse de l’intérêt et contraction de l’offre avant revalorisation. Les deux observations portent sur la même variante, mais ne prouvent pas une causalité.</p>
 {c.absorption&&<p>Contexte historique : {c.absorption.paid_count}/{c.absorption.cohort_count} annonces suivies ont une vente documentée sous 14 jours.</p>}
 <details className="radar-disclosure"><summary>Risques et preuves</summary><p>Vérifier les remises en vente, la représentativité des relevés, les réassorts, le prix d’entrée et les frais. Une offre disparue n’est pas une vente. L’absorption historique n’est pas une probabilité de revente.</p><p>Parcours d’offre : {s.prior_at.slice(0,10)} → {s.current_at.slice(0,10)}.</p><ul>{d.evidence.map(e=><li key={e.lot_id}><a href={"https://gradedcardcenter.com/item/"+e.lot_id.slice(4)} target="_blank" rel="noopener noreferrer">{e.sold_day} · {euros.format(e.price_cents/100)} ↗</a></li>)}</ul></details>
 </article>;
 })}
 <p className="radar-sales-description">Classement exploratoire, limité aux résultats des modules existants. Aucun filtre de capital ; aucune probabilité ou hausse future inventée.</p>
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
 <h3>Raréfaction des offres à prix fixe</h3>
 <p>Comparaison de deux parcours complets espacés de 7 à 14 jours. Le relevé récent doit dater de moins de 48 h.</p>
 {supply===null?<p>Historique de l’offre momentanément indisponible.</p>:supply.length===0?<p>Aucune contraction qualifiée ou historique encore insuffisant.</p>:supply.slice(0,15).map(s=>{
 const demand=report?.items.find(p=>p.variant===s.variant_key);
 const v=variants.find(v=>v.key===s.variant_key);
 return <article className="edge-mri-case" key={s.variant_key}>
 <small>{demand?"CONVERGENCE OFFRE / VENTES":"SIGNAL D’OFFRE"} · À INVESTIGUER</small>
 <h3>{v?.name??s.title}</h3>
 <p>{s.prior_count} → {s.current_count} offres relevées (−{supplyContraction(s).toFixed(1)} %).</p>
 <p>{s.prior_at.slice(0,10)} → {s.current_at.slice(0,10)}.</p>
 {demand&&<p>Ventes relevées : {demand.priorCount} → {demand.recentCount} ; médiane {demand.change.toFixed(1)} %. Les deux signaux concernent la même variante.</p>}
 <p>Une disparition ne prouve pas une vente. Les enchères ne sont pas incluses.</p>
 </article>;
 })}
 <h3>Absorption commerciale à 14 jours</h3>
 <p>Part des annonces nouvellement observées dont une vente payée a été documentée dans les 14 jours suivants. Une première observation n’est pas une date de publication certaine.</p>
 {absorption===null?<p>Analyse de l’absorption momentanément indisponible.</p>:absorption.length===0?<p>Historique arrivé à maturité encore insuffisant.</p>:absorption.slice(0,15).map(a=>{
 const v=variants.find(v=>v.key===a.variant_key);
 return <article className="edge-mri-case" key={"absorption-"+a.variant_key}>
 <h3>{v?.name??a.title}</h3>
 {v&&<p>{v.variant}</p>}
 <div className="radar-sale-price"><strong>{absorptionRate(a)?.toFixed(1)} %</strong><span>Ventes payées documentées</span></div>
 <p>{a.paid_count} sur {a.cohort_count} annonces suivies.</p>
 <p>{a.median_delay_days===null?"Aucun délai de vente documenté":`Délai médian parmi les ventes documentées : ${a.median_delay_days.toFixed(1)} jours`}</p>
 <p>{a.cohort_count-a.paid_count} sans preuve de vente dans la fenêtre ; leur issue reste indéterminée.</p>
 </article>;
 })}
 <p>Échantillon : premières observations précédées d’un parcours complet récent, cohortes âgées de 15 à 75 jours et au moins cinq annonces par variante. Ventes du jour initial exclues faute d’heure fiable. Le taux est un minimum documenté, pas une probabilité de revente.</p>
 <p className="radar-sales-description">Critères exploratoires : au moins 3 puis 5 ventes relevées, hausse du volume d’au moins 50 %, médiane dans ±5 %. La couverture historique peut être incomplète ; les volumes relevés ne représentent pas nécessairement le marché entier.</p>
 </section>;
}
