// Privacy-preserving read-only browser view of ingested Leboncoin excerpts.
// An Access-signed single operator is mandatory; the D1 schema currently
// supports one private collector owner, not publicly shared multi-tenancy.
import {verifyCloudflareAccessSession} from "./leboncoin-access-session.mjs";
import {scoreLeboncoinLead,sortLeboncoinLeads} from "./leboncoin-lead-triage.mjs";
import {comparablePaidSales} from "./leboncoin-paid-comparables.mjs";
import {discoverPackagedCandidates} from "./leboncoin-product-candidates.mjs";

const HEADERS={
  "Content-Type":"text/html; charset=utf-8",
  "Cache-Control":"no-store, private",
  "Referrer-Policy":"no-referrer",
  "X-Content-Type-Options":"nosniff",
  "Content-Security-Policy":"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
};
const escape=s=>String(s??"").replace(/[&<>"']/g,c=>({
  "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
})[c]);
const notFound=()=>new Response("Not found",{status:404,headers:HEADERS});
function sanitized(row,now){
  if(!row || typeof row.listing_id!=="string" ||
    !/^leboncoin:[0-9]{1,20}$/.test(row.listing_id))return null;
  const id=row.listing_id.slice("leboncoin:".length);
  const canonical="https://www.leboncoin.fr/vi/"+id+".htm";
  if(row.source_url!==canonical)return null;
  const observed=typeof row.observed_at==="string" && Number.isFinite(Date.parse(row.observed_at))
    ? row.observed_at:null;
  const age=observed?Math.max(0,(now-Date.parse(observed))/3600000):null;
  const freshness=age===null?"DATE INCONNUE":age<=24?"MOINS DE 24 H":age<=48?"24–48 H":"PLUS DE 48 H";
  return {
    id,title:typeof row.title==="string"&&row.title.trim()?row.title.slice(0,180):"Annonce sans titre",
    price:Number.isSafeInteger(row.price_cents)&&row.price_cents>=0?row.price_cents:null,
    location:typeof row.location==="string"?row.location.slice(0,150):"",
    search:typeof row.search_name==="string"?row.search_name.slice(0,150):"",
    observed, freshness,canonical,
    alertHits:Number.isSafeInteger(row.alert_hits)&&row.alert_hits>0?row.alert_hits:1,
    emailExtracted:Number.isSafeInteger(row.extracted_count)&&row.extracted_count>=0?row.extracted_count:null,
    emailAdvertised:Number.isSafeInteger(row.advertised_count)&&row.advertised_count>=0?row.advertised_count:null,
    firstPrice:Number.isSafeInteger(row.first_price_cents)&&row.first_price_cents>=0?row.first_price_cents:null,
    firstObserved:typeof row.first_observed_at==="string"&&Number.isFinite(Date.parse(row.first_observed_at))?row.first_observed_at:null
  };
}
const money=new Intl.NumberFormat("fr-FR",{style:"currency",currency:"EUR"});
export function renderOutlookOffers(rows,{now=Date.now(),paidSales=null}={}){
  const offers=sortLeboncoinLeads((Array.isArray(rows)?rows:[]).slice(0,50),now)
    .map(row=>{
      const safe=sanitized(row,now);
      return safe?{...safe,lead:scoreLeboncoinLead(row,now),
        comparable:comparablePaidSales(safe.title,paidSales,now)}:null;
    }).filter(Boolean);
  const candidates=discoverPackagedCandidates(paidSales,{now}).candidates;
  const tiles=offers.map(row=>`<article class="offer">
    <div class="top"><span class="source">LEBONCOIN · EMAIL</span><span class="fresh">${escape(row.freshness)}</span></div>
    <div class="lead" data-signal="${escape(row.lead.kind)}">${escape(row.lead.label)}${row.lead.kind==="PRICE_DROP" ? " · "+escape(row.lead.changePercent.toFixed(1))+" %":""}</div>
    <h2>${escape(row.title)}</h2><strong class="price">${row.price===null?"Prix non renseigné":escape(money.format(row.price/100))}</strong>
    <div class="meta">${row.search?"Recherche : "+escape(row.search):"Recherche non renseignée"}${row.location?" · "+escape(row.location):""}</div>
    <div class="meta">Signalé le ${row.observed?escape(row.observed):"date inconnue"} · ${row.alertHits} alerte(s) distincte(s)</div>
    ${row.alertHits>1 && row.price!==null && row.firstPrice!==null ?
      `<div class="history">Prix signalé initialement : ${escape(money.format(row.firstPrice/100))} · Variation : ${escape(money.format((row.price-row.firstPrice)/100))}</div>`:""}
    ${row.alertHits>1 && row.firstObserved?
      `<div class="meta">Premier signalement : ${escape(row.firstObserved)}</div>`:""}
    <div class="meta">${row.emailExtracted!==null&&row.emailAdvertised!==null?escape(row.emailExtracted+" extraits sur "+row.emailAdvertised+" résultats annoncés dans le dernier email"):"Nombre de résultats du dernier email non disponible"}</div>
    <div class="comparable">
      ${row.comparable.status==="COMPARABLE"
        ? `<strong>Ventes payées GCC comparables · ${row.comparable.saleCount} transactions / 90 jours</strong><span>Médiane brute : ${escape(money.format(row.comparable.medianCents/100))} · Bas observé : ${escape(money.format(row.comparable.lowCents/100))}</span>${row.price!==null?`<span>Écart brut avec le bas des ventes : ${escape(money.format((row.comparable.lowCents-row.price)/100))} · hors frais, livraison et risque de variante</span>`:""}<small>Correspondance stricte de la variante déclarée (carte gradée ou scellé), sans vérification physique. Aucun frais ni transport déduit.</small>`
        : "<span>Ventes payées comparables non établies · Identité complète à vérifier (série, référence, langue, édition et grade ou format scellé).</span>"}
    </div>
    <details><summary>Vérification & provenance</summary>
      <p>Prix demandé extrait d’un email. Annonce non revérifiée sur Leboncoin.
      Disponibilité inconnue, transaction non confirmée et photo non collectée.</p>
      <p>Référence d'annonce : ${escape(row.id)}</p>
    </details>
    <a href="${row.canonical}" target="_blank" rel="noopener noreferrer">Consulter l'annonce d'origine ↗</a>
  </article>`).join("");
  return `<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>EDGE — Alertes Leboncoin</title><style>
  :root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0b101a;color:#ecf1fa;font:14px system-ui,-apple-system,sans-serif}
  main{max-width:1120px;margin:auto;padding:40px 24px 72px}header{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;border-bottom:1px solid #283347;padding-bottom:24px}
  h1{font-size:clamp(26px,4vw,42px);letter-spacing:-1.2px;margin:9px 0}.eyebrow,.source,.fresh{font:11px ui-monospace,monospace;letter-spacing:1px;color:#adc1e5}
  .sub{color:#9cacbf;max-width:700px;line-height:1.7} .count{color:#a8e0cc}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,290px),1fr));gap:14px;margin-top:28px}
  .offer{background:#121a28;border:1px solid #283448;border-radius:13px;padding:22px;min-width:0;display:flex;flex-direction:column;gap:12px}
  .top{display:flex;justify-content:space-between;align-items:center;gap:9px;flex-wrap:wrap}.fresh{color:#e1bd8c}
  h2{font-size:17px;margin:1px 0 0;line-height:1.35}.price{font-size:24px;color:#bbebde}
  .lead{font-size:11px;letter-spacing:.15px;color:#b3c4dc;background:#1a2637;border:1px solid #304159;border-radius:6px;padding:7px 9px}
  .lead[data-signal="PRICE_DROP"]{color:#b5eed8;border-color:#326955;background:#142a27}
  .lead[data-signal="REPEATED"]{color:#f0d2a1;border-color:#725b34}
  .comparable{display:flex;flex-direction:column;gap:6px;border-top:1px solid #2b384d;padding-top:12px;color:#a0b0c7;font-size:12px;line-height:1.6}
  .comparable strong{color:#c3eedf}.comparable small{color:#859ab2}
  .meta{font-size:12px;color:#9bacbf;line-height:1.6}.history{font-size:12px;color:#bde7cd;line-height:1.5}details{border-top:1px solid #2e3b4f;padding-top:12px;color:#9eafc7;line-height:1.7}
  summary{cursor:pointer;color:#cad7eb}a{margin-top:auto;color:#a4d7ec;font-weight:650;text-decoration:none}a:hover{text-decoration:underline}
  .empty{margin-top:28px;background:#121a28;border:1px dashed #344056;padding:25px;border-radius:12px;color:#aebbcf}
  .candidate-list{margin-top:18px;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,290px),1fr));gap:12px}.candidate{background:#111b2a;padding:16px 20px;border:1px solid #293c53;border-radius:11px}.candidate h3{font-size:15px;margin:8px 0}.candidate .meta{line-height:1.7}
  .candidate-section{margin-top:44px;padding-top:24px;border-top:1px solid #283347}.candidate-section h2{font-size:22px;letter-spacing:-.4px}
  </style></head><body><main><header><div><div class="eyebrow">EDGE / RADAR / SOURCES PRIVÉES</div>
  <h1>Alertes Leboncoin<span style="color:#8dd7bf">.</span></h1>
  <p class="sub">Annonces extraites des emails Outlook et enregistrées dans D1. Les baisses de prix sont des signaux à examiner, pas des opportunités prouvées. Aucune vente ou disponibilité n’est confirmée.</p>
  </div><span class="count">${offers.length} annonce(s) distincte(s)</span></header>
  ${offers.length?`<section class="grid" aria-label="Annonces observées">${tiles}</section>`:
    '<div class="empty">Aucune annonce importée. EDGE n’affiche pas de données fictives.</div>'}
  <p class="sub">Jusqu’à 50 annonces distinctes récentes, classées par signaux puis fraîcheur · Critère de tri : baisse d’au moins 5 % et 5 €, dernier signalement datant de moins de 48 h · Données issues des emails, sans vérification en direct.</p>
  <section class="candidate-section"><h2>Références scellées à vérifier</h2>
    <p class="sub">Candidats automatiquement découverts dans les identifiants de ventes GCC. Aucune identité constructeur vérifiée : ces entrées ne peuvent pas servir à établir une comparaison de prix.</p>
    ${candidates.length?'<div class="candidate-list">'+candidates.map(item=>`<article class="candidate"><span class="eyebrow">CANDIDAT · NON VÉRIFIÉ</span><h3>${escape(item.packaging.toUpperCase()+" · "+item.product.replaceAll("-"," "))}</h3><div class="meta">Série : ${escape(item.series.replaceAll("-"," "))} · Langue : ${escape(item.language.toUpperCase())} · Édition : ${escape(item.edition)} · Quantité déclarée : ${item.units}</div><div class="meta">${item.paidLotCount} lot(s) GCC daté(s) · Dernière vente : ${escape(item.latestPaidDay)}</div><div class="meta">À vérifier : référence officielle, composition exacte, langue et identifiants produit.</div></article>`).join("")+'</div>':
      '<div class="empty">Aucun candidat vérifiable à partir des lignes GCC actuellement accessibles. Aucun produit inventé.</div>'}
  </section>
  </main></body></html>`;
}
export async function handleOutlookOffers({
  request,env,fetchImpl=fetch,verifySession=verifyCloudflareAccessSession,
  now=()=>Date.now()
}){
  const url=new URL(request.url);
  if(url.pathname!=="/internal/outlook/offers")return null;
  if(env?.OUTLOOK_ROUTES_ENABLED!=="true"||env?.OUTLOOK_OFFERS_ENABLED!=="true")
    return notFound();
  if(request.method!=="GET"||url.protocol!=="https:"||url.search||url.hash||
    request.headers.has("Authorization")||request.headers.has("X-Owner-Key"))
    return notFound();
  let callback;
  try{callback=new URL(env.OUTLOOK_REDIRECT_URI)}catch{return notFound()}
  if(callback.origin!==url.origin)return notFound();
  const subjects=typeof env.CF_ACCESS_ALLOWED_SUBJECTS==="string"
    ?env.CF_ACCESS_ALLOWED_SUBJECTS.split(",").map(x=>x.trim()).filter(Boolean):[];
  if(subjects.length!==1||!env.CF_ACCESS_TEAM_DOMAIN||!env.CF_ACCESS_APP_AUD)
    return notFound();
  try{
    const identity=await verifySession(request,{
      teamUrl:env.CF_ACCESS_TEAM_DOMAIN,audience:env.CF_ACCESS_APP_AUD,
      allowedSubjects:subjects,fetchImpl
    });
    if(identity?.authenticated!==true||!/^[a-f0-9]{64}$/i.test(identity.ownerKey||""))
      return notFound();
  }catch{return notFound()}
  if(typeof env.DB?.prepare!=="function")
    return new Response("Données momentanément indisponibles",{status:503,headers:HEADERS});
  try{
    // One card per listing ID, but preserve repeat observations as history.
    // Email announced counts are NOT the number of ads actually in the email.
    const data=await env.DB.prepare(`WITH ranked AS (
      SELECT o.listing_id,o.observed_at,o.source_url,o.title,
        o.price_cents,o.location,m.search_name,m.advertised_count,
        m.extracted_count,COUNT(*) OVER (PARTITION BY o.listing_id) AS alert_hits,
        MIN(o.observed_at) OVER (PARTITION BY o.listing_id) AS first_observed_at,
        FIRST_VALUE(o.price_cents) OVER (
          PARTITION BY o.listing_id ORDER BY o.observed_at ASC,o.message_id ASC
        ) AS first_price_cents,
        ROW_NUMBER() OVER (
          PARTITION BY o.listing_id
          ORDER BY o.observed_at DESC,o.message_id DESC
        ) AS rn
      FROM lbc_listing_observations o
      JOIN lbc_alert_messages m ON m.message_id=o.message_id
    )
    SELECT listing_id,observed_at,source_url,title,price_cents,location,
      search_name,advertised_count,extracted_count,alert_hits,
      first_observed_at,first_price_cents
    FROM ranked WHERE rn=1 ORDER BY observed_at DESC,listing_id DESC LIMIT 50`).all();
    if(!Array.isArray(data?.results)||data.results.length>50)throw Error("bad_d1_response");
    // Optional: only a verified real paid-sale ledger is comparable. If it
    // is absent or unreadable, display NO comparison instead of made-up value.
    let paidSales=null;
    try{
      const sales=await env.DB.prepare(`SELECT variant_key,lot_id,sold_day,price_cents,source_url
        FROM paid_market_sales WHERE sold_day>=? AND sold_day<=?
        ORDER BY sold_day DESC,lot_id LIMIT 1001`)
        .bind(new Date(now()-90*86400000).toISOString().slice(0,10),
          new Date(now()).toISOString().slice(0,10)).all();
      if(Array.isArray(sales?.results) && sales.results.length<=1000)
        paidSales=sales.results;
    }catch{/* Incomplete schema or absent ledger must not be treated as sales. */}
    return new Response(renderOutlookOffers(data.results,{now:now(),paidSales}),{status:200,headers:HEADERS});
  }catch{
    return new Response("Données momentanément indisponibles",{status:503,headers:HEADERS});
  }
}
