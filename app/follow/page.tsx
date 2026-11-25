import Link from "next/link";
import {getFollowedLots,followPage} from "../lib/automatic-follow";
import {getCatalystDiscoveries} from "../lib/catalyst-discoveries";
export const dynamic="force-dynamic";
const money=new Intl.NumberFormat("fr-FR",{style:"currency",currency:"EUR"});
const price=(c:number|null)=>c===null?"—":money.format(c/100);
const day=(s:string|null)=>s?s.slice(0,10):"Non renseigné";
export default async function FollowPage({searchParams}:{searchParams:Promise<{page?:string}>}){
 const page=followPage((await searchParams).page);
 const [lots,catalysts]=await Promise.all([getFollowedLots(page),getCatalystDiscoveries()]);
 return <div className="native-dashboard edge-follow">
 <header className="edge-portfolio-heading"><p className="native-eyebrow">MÉMOIRE DU MARCHÉ</p><h1>Suivi<span>.</span></h1><p>Les pistes conservées automatiquement par EDGE, quel que soit votre capital.</p></header>
 <section className="edge-follow-panel"><h2>Opportunités mémorisées</h2><p>Dernière évaluation de chaque annonce déjà qualifiée. Le prix relevé n’est pas nécessairement encore disponible.</p>
 {lots===null?<p>Historique momentanément indisponible.</p>:lots.items.length===0?<p>Aucune opportunité mémorisée sur cette page.</p>:<div className="edge-follow-list">{lots.items.map(l=>{
 const state=l.paid_day?"Vente payée documentée":l.latest_visibility==="NOT_SEEN"?"Annonce non retrouvée":l.status==="INVESTIGATE"?"À approfondir":"À réévaluer";
 const sameLot=/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(l.lot_id);
 return <article key={l.lot_id} className="edge-follow-card"><div className="edge-follow-state">{state}</div><h3>{l.title}</h3><small>Repérée le {day(l.first_seen)} · Évaluée le {day(l.observed_at)}</small><div className="edge-follow-prices"><div><span>Premier prix qualifié</span><strong>{price(l.initial_cents)}</strong></div><div><span>Dernier prix évalué</span><strong>{price(l.asking_cents)}</strong></div><div><span>Médiane comparable</span><strong>{price(l.median_cents)}</strong></div></div><details><summary>Historique et preuves</summary><p>{l.variant_key??"Variante non confirmée"} · {l.comparable_count} ventes comparables.</p><p>Marge théorique avant frais d’achat : {price(l.headroom_cents)}. Dernière observation : {day(l.latest_seen)}.</p>{l.paid_day&&<p>Vente documentée le {day(l.paid_day)}.</p>}<p>La variation de prix demandé n'est pas un rendement réalisé. Une annonce non retrouvée n’est pas une vente.</p></details>{sameLot&&<a href={"https://gradedcardcenter.com/item/"+l.lot_id} target="_blank" rel="noopener noreferrer">Consulter la source GCC ↗</a>}</article>
 })}</div>}
 <nav className="edge-follow-pages" aria-label="Pages du suivi">{page>1&&<Link href={"/follow?page="+(page-1)}>Précédente</Link>}{lots?.hasNext&&page<1000&&<Link href={"/follow?page="+(page+1)}>Suivante</Link>}</nav></section>
 <section className="edge-follow-panel"><h2>Catalyseurs suivis</h2><p>Dernières publications officielles repérées par EDGE (40 maximum).</p>{catalysts===null?<p>Publications momentanément indisponibles.</p>:catalysts.items.length===0?<p>Aucune publication mémorisée.</p>:<div className="edge-follow-list">{catalysts.items.map(c=><article key={c.source_url} className="edge-follow-card"><small>{c.publisher} · Repérée le {day(c.first_seen_at)}</small><h3>{c.title}</h3><p>{c.investigation_status==="READ"?"Publication consultée":c.investigation_status==="FAILED"?"Consultation à renouveler":"À investiguer"}</p>{c.description&&<details><summary>Informations de l’éditeur</summary><p>{c.description}</p></details>}<a href={c.source_url} target="_blank" rel="noopener noreferrer">Publication originale ↗</a></article>)}</div>}<Link href="/mri?tab=signaux#edge-radar-catalysts">Ouvrir les investigations →</Link></section>
 </div>
}
