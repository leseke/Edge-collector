import {getCatalystDiscoveries} from "../lib/catalyst-discoveries";
import Link from "next/link";
import {catalystLeads,type CatalystKind} from "../lib/catalyst-intelligence";
import type {MarketSnapshot} from "../lib/market-data";
const labels:Record<CatalystKind,string>={REPRINT:"Réimpression / réassort",EXCLUSIVITY:"Exclusivité potentielle",ANNIVERSARY:"Anniversaire",COLLABORATION:"Collaboration",RELEASE:"Sortie / lancement",OTHER:"Publication à qualifier"};
const questions:Record<CatalystKind,string>={REPRINT:"Vérifier l’ampleur de la nouvelle offre et le risque de dilution de la rareté.",EXCLUSIVITY:"Vérifier les quantités, les territoires, les modalités de distribution et la possibilité de réédition.",ANNIVERSARY:"Identifier les produits concernés, la portée de l’événement et les précédents comparables.",COLLABORATION:"Vérifier les licences concernées, les publics susceptibles de converger et les produits réellement annoncés.",RELEASE:"Vérifier la date, le prix initial, les conditions d’accès et les différenciations du produit.",OTHER:"Identifier les faits annoncés et les mécanismes possibles de réaction commerciale."};
export async function CatalystPanel({snapshot}:{snapshot:MarketSnapshot}){
 const leads=catalystLeads(snapshot.reactionCases);
 const discoveries=await getCatalystDiscoveries();
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
 <h3>Comparaisons interboutiques</h3>
 {discoveries===null?<p>Comparaison indisponible.</p>:discoveries.comparisons.length===0?<p>Aucune paire d’offres fraîches de même GTIN et de même disponibilité.</p>:discoveries.comparisons.map((g:{key:string;spreadCents:number;offers:{merchant:string;url:string;name?:string;priceCents:number;availability:string;observedAt:string}[]})=><article className="edge-mri-case" key={g.key}><h4>{g.offers[0].name??g.key}</h4><p>Écart affiché hors livraison : {(g.spreadCents/100).toFixed(2)} €</p><ul>{g.offers.map(o=><li key={o.url}><a href={o.url} target="_blank" rel="noopener noreferrer">{o.merchant}</a> · {(o.priceCents/100).toFixed(2)} € · {o.availability} · {o.observedAt.slice(0,10)}</li>)}</ul><p>GTIN déclaré identique ; langue, contenu et livraison à confirmer avant achat.</p></article>)}
 <h3>Découvertes autonomes des éditeurs</h3>
 {discoveries===null?<p>Collecte des éditeurs momentanément indisponible.</p>:<>
 <p>{discoveries.scan?("Dernier passage : "+new Date(discoveries.scan.observed_at).toLocaleString("fr-FR",{timeZone:"Europe/Paris"})+" · "+(discoveries.scan.status==="FAILED"?"Source inaccessible ou extraction impossible":discoveries.scan.status==="EMPTY"?"Aucune nouvelle publication":"Nouvelles publications : "+discoveries.scan.discovered)):"Aucun passage enregistré."}</p>
 {discoveries.items.length===0?<p>Aucune découverte enregistrée.</p>:discoveries.items.map(p=><article className="edge-mri-case" key={p.source_url}>
 <small>{labels[p.kind]} · WATCH</small>
 <h3>{p.title}</h3>
 <p>{p.publisher} · Repérée le {p.first_seen_at.slice(0,10)} (date de publication non vérifiée).</p>
 <p>Investigation : {questions[p.kind]}</p>
 <details className="radar-disclosure"><summary>Dossier d’investigation</summary>
 <p>{p.investigation_status==="READ"?"Métadonnées de la publication consultées":p.investigation_status==="FAILED"?"Consultation échouée · nouvelle tentative prévue":"En attente de consultation"}</p>
 {p.headline&&<p>{p.headline}</p>}
 {p.description&&<p>{p.description}</p>}
 {p.published_at&&<p>Date indiquée par l’éditeur : {p.published_at.slice(0,10)}</p>}
 {p.investigated_at&&<p>Dernière investigation : {p.investigated_at.slice(0,10)}</p>}
 <p>Informations déclarées par l’éditeur, non corroborées indépendamment.</p>
 <h4>Correspondances commerciales à vérifier</h4>
 <p>{discoveries.commercial.length?discoveries.commercial.map(m=>`${m.merchant} : ${m.observedAt.slice(0,10)} · ${m.status==="READ"?"Consulté":"Collecte échouée"}`).join(" / "):"Catalogues non encore relevés."}</p>
 {p.commercialCandidates.length===0?<p>Aucune correspondance candidate dans ce relevé.</p>:<ul>{p.commercialCandidates.map(c=><li key={c.url}><a href={c.url} target="_blank" rel="noopener noreferrer">{c.title}</a> · Mots communs : {c.overlap.join(", ")}{c.offer?.status==="READ"?<div><p>{c.offer.name??"Nom non renseigné"} {c.offer.sku&&`· SKU ${c.offer.sku}`}</p><p>{typeof c.offer.priceCents==="number"&&c.offer.currency?`${(c.offer.priceCents/100).toFixed(2)} ${c.offer.currency}`:"Prix non renseigné"} · {c.offer.availability??"UNKNOWN"}</p><p>Relevé du {c.offer.observedAt.slice(0,10)}{!c.offer.fresh?" · ancien, à revérifier":""}</p></div>:<p>{c.offer?"Extraction échouée":"Fiche non consultée"}</p>}</li>)}</ul>}
 <p>Prix et disponibilité éventuellement déclarés par le marchand sur la fiche candidate. Correspondance exacte avec la publication et livraison non confirmées.</p>
 <p>À rechercher : identité exacte, disponibilité française, prix d’entrée, distribution, rareté et éléments contraires à la thèse.</p>
 </details>
 <p>Produit exact, prix d’entrée et disponibilité en France à confirmer. Pas de décision d’achat automatique.</p>
 <a href={p.source_url} target="_blank" rel="noopener noreferrer">Source éditeur ↗</a>
 </article>)}</>}
 <p className="radar-sales-description">Une publication peut être incomplète ou indirectement liée au produit. La classification ne certifie ni la fiabilité de la source ni la réalité de l’événement.</p>
 </section>;
}
