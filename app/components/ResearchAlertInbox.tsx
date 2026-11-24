import Link from "next/link";
import {alertFilter,alertPage,alertEvidence,getResearchAlerts,type AlertReason} from "../lib/research-alerts";
const labels:Record<AlertReason,string>={NEW_OPPORTUNITY:"Nouvelle opportunité",STATUS_IMPROVED:"Valorisation améliorée",PRICE_DROP:"Baisse significative",REAPPEARED:"Annonce retrouvée"};
const money=new Intl.NumberFormat("fr-FR",{style:"currency",currency:"EUR"});
const date=new Intl.DateTimeFormat("fr-FR",{dateStyle:"short",timeStyle:"short",timeZone:"Europe/Paris"});
const format=(cents:number)=>money.format(cents/100);
export async function ResearchAlertInbox({params}:{params:Record<string,unknown>}){
 const filter=alertFilter(params.alert),page=alertPage(params.alertPage);
 const data=await getResearchAlerts(filter,page);
 const href=(p:number,f:string=filter)=>"/mri?tab=signaux&alert="+f+"&alertPage="+p+"#edge-alerts";
 return <section id="edge-alerts" className="dashboard-section radar-section" aria-labelledby="edge-alerts-title">
  <h2 id="edge-alerts-title">Centre de notifications</h2>
  <p className="radar-sales-description">Alertes historiques générées par le collecteur EDGE. Aucun achat automatique.</p>
  <nav className="radar-offer-links" aria-label="Filtrer les notifications">
   <Link href={href(1,"all")} aria-current={filter==="all"?"page":undefined}>Toutes</Link>
   {Object.entries(labels).map(([key,label])=><Link key={key} href={href(1,key)} aria-current={filter===key?"page":undefined}>{label}</Link>)}
  </nav>
  {data===null?<p>Centre de notifications momentanément indisponible.</p>:data.items.length===0?<p>Aucune alerte enregistrée pour cette sélection.</p>:data.items.map(a=>{
   const stale=Date.now()-Date.parse(a.observed_at)>48*3600000;
   const evidence=alertEvidence(a);
   return <article key={a.lot_id+":"+a.cycle+":"+a.page} className="edge-mri-case">
    <small>{labels[a.reason]} · {date.format(new Date(a.observed_at))}{stale?" · Archive":""}</small>
    <h3>{a.title}</h3>
    <div className="radar-sale-price"><strong>{format(a.asking_cents)}</strong><span>Prix au moment de l’alerte</span></div>
    {a.previous_cents!==null&&<p>Prix de référence précédent : {format(a.previous_cents)}</p>}
    <p>{a.status==="INVESTIGATE"?"À approfondir":a.status==="THIN_MARGIN"?"Marge fragile":a.status==="NO_DISCOUNT"?"Décote non démontrée":"Comparables insuffisants"}</p>
    <p>{a.paid_day?"Vente payée documentée le "+a.paid_day:a.latest_visibility==="NOT_SEEN"?"Annonce non retrouvée, vente non confirmée":"Disponibilité actuelle à vérifier."}</p>
    <details className="radar-disclosure">
      <summary>Justification et preuves historiques</summary>
      <p>{a.variant_key?"Variante : "+a.variant_key:"Variante non confirmée"}</p>
      <p>{a.comparable_count} ventes comparables au moment de l’évaluation.</p>
      {a.median_cents!==null&&<p>Médiane : {format(a.median_cents)}</p>}
      {a.headroom_cents!==null&&<p>Marge théorique avant frais d’achat : {format(a.headroom_cents)} (frais de revente supposés : {a.resale_fee_percent} %).</p>}
      {a.latest_seen&&<p>Dernier relevé : {date.format(new Date(a.latest_seen))}</p>}
      {evidence.length>0&&<ul>{evidence.map(s=><li key={s.id}><a href={s.source} target="_blank" rel="noopener noreferrer">{format(s.cents)} · {s.day} · Vente payée ↗</a></li>)}</ul>}
    </details>
    {/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(a.lot_id)&&<a className="radar-sale-source" href={"https://gradedcardcenter.com/item/"+a.lot_id} target="_blank" rel="noopener noreferrer">Voir la source GCC ↗</a>}
   </article>;
  })}
  <nav className="radar-actions" aria-label="Pages des notifications">
   {page>1&&<Link className="radar-action" href={href(page-1)}>Précédente</Link>}
   {data?.hasNext&&page<1000&&<Link className="radar-action" href={href(page+1)}>Suivante</Link>}
  </nav>
 </section>;
}
