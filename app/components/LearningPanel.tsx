import {getLearningReport} from "../lib/edge-learning";
const labels:Record<string,string>={NEW_OPPORTUNITY:"Nouvelle opportunité",STATUS_IMPROVED:"Valorisation améliorée",PRICE_DROP:"Baisse significative",REAPPEARED:"Réapparition"};
export async function LearningPanel(){
 const report=await getLearningReport();
 return <section className="dashboard-section radar-section" aria-labelledby="learning-title">
 <h2 id="learning-title">Pertinence des signaux</h2>
 <p>Comparaison des médianes de ventes payées avant le signal et sur les 30 jours suivants, pour une même variante. Ce n’est pas un rendement d’investissement.</p>
 {report===null?<p>Évaluation momentanément indisponible.</p>:report.groups.length===0?<p>Aucune cohorte arrivée à maturité avec référence initiale suffisante.</p>:<>
 {report.partial&&<p>Échantillon limité aux 100 cohortes les plus récentes.</p>}
 {report.groups.map(g=><article className="edge-mri-case" key={g.reason}>
 <h3>{labels[g.reason]??g.reason}</h3>
 <p>{g.evaluable} cohortes évaluables sur {g.eligible} éligibles.</p>
 {g.medianChange===null?<p>Ventes ultérieures insuffisantes.</p>:<>
 <p>Variation médiane : {g.medianChange.toFixed(1)} %</p>
 <p>{g.up} en hausse (&gt;5 %) · {g.flat} stables · {g.down} en baisse (&gt;5 %).</p>
 </>}
 </article>)}</>}
 <p className="radar-sales-description">Une première alerte par variante et motif sur 180 jours, fenêtre de suivi achevée et trois ventes ultérieures au minimum. Pas de classement automatique des stratégies ni d’inférence causale.</p>
 </section>;
}
