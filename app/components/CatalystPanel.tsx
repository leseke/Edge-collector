import Link from "next/link";
import {catalystLeads,type CatalystKind} from "../lib/catalyst-intelligence";
import type {MarketSnapshot} from "../lib/market-data";
const labels:Record<CatalystKind,string>={REPRINT:"Réimpression / réassort",EXCLUSIVITY:"Exclusivité potentielle",ANNIVERSARY:"Anniversaire",COLLABORATION:"Collaboration",RELEASE:"Sortie / lancement",OTHER:"Publication à qualifier"};
const questions:Record<CatalystKind,string>={REPRINT:"Vérifier l’ampleur de la nouvelle offre et le risque de dilution de la rareté.",EXCLUSIVITY:"Vérifier les quantités, les territoires, les modalités de distribution et la possibilité de réédition.",ANNIVERSARY:"Identifier les produits concernés, la portée de l’événement et les précédents comparables.",COLLABORATION:"Vérifier les licences concernées, les publics susceptibles de converger et les produits réellement annoncés.",RELEASE:"Vérifier la date, le prix initial, les conditions d’accès et les différenciations du produit.",OTHER:"Identifier les faits annoncés et les mécanismes possibles de réaction commerciale."};
export function CatalystPanel({snapshot}:{snapshot:MarketSnapshot}){
 const leads=catalystLeads(snapshot.reactionCases);
 return <section className="dashboard-section radar-section" aria-labelledby="catalyst-title">
 <h2 id="catalyst-title">Radar des catalyseurs</h2>
 <p>Publications déjà collectées par EDGE, toutes catégories confondues. Classification exploratoire à partir du titre, sans exiger de ventes antérieures.</p>
 {snapshot.status==="UNAVAILABLE"?<p>Publications momentanément indisponibles.</p>:leads.length===0?<p>Aucun catalyseur documenté dans le relevé disponible.</p>:leads.map(p=><article className="edge-mri-case" key={p.productId+"|"+p.url}>
 <small>{labels[p.kind]} · SIGNAL À VÉRIFIER</small>
 <h3>{p.title}</h3>
 <p>{p.host} · {p.publishedAt?p.publishedAt.slice(0,10):"Date non confirmée"}</p>
 <p>Produit lié par le relevé : {snapshot.cards.find(c=>c.productId===p.productId)?.name??p.productId} · {p.relationship}</p>
 <p>Investigation : {questions[p.kind]}</p>
 <p>Son impact commercial reste à vérifier. Aucun rendement présumé.</p>
 <a href={p.url} target="_blank" rel="noopener noreferrer">Consulter la publication ↗</a>
 {snapshot.cards.some(c=>c.productId===p.productId)&&<p><Link href={"/explorer/"+encodeURIComponent(p.productId)}>Examiner le produit</Link></p>}
 </article>)}
 <p className="radar-sales-description">Une publication peut être incomplète ou indirectement liée au produit. La classification ne certifie ni la fiabilité de la source ni la réalité de l’événement.</p>
 </section>;
}
