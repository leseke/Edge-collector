// Privacy-preserving read-only browser view of ingested Leboncoin excerpts.
// An Access-signed single operator is mandatory; the D1 schema currently
// supports one private collector owner, not publicly shared multi-tenancy.
import {verifyCloudflareAccessSession} from "./leboncoin-access-session.mjs";

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
    emailAdvertised:Number.isSafeInteger(row.advertised_count)&&row.advertised_count>=0?row.advertised_count:null
  };
}
const money=new Intl.NumberFormat("fr-FR",{style:"currency",currency:"EUR"});
export function renderOutlookOffers(rows,{now=Date.now()}={}){
  const offers=(Array.isArray(rows)?rows:[]).slice(0,50).map(row=>sanitized(row,now)).filter(Boolean);
  const tiles=offers.map(row=>`<article class="offer">
    <div class="top"><span class="source">LEBONCOIN · EMAIL</span><span class="fresh">${escape(row.freshness)}</span></div>
    <h2>${escape(row.title)}</h2><strong class="price">${row.price===null?"Prix non renseigné":escape(money.format(row.price/100))}</strong>
    <div class="meta">${row.search?"Recherche : "+escape(row.search):"Recherche non renseignée"}${row.location?" · "+escape(row.location):""}</div>
    <div class="meta">Signalé le ${row.observed?escape(row.observed):"date inconnue"} · ${row.alertHits} alerte(s) distincte(s)</div>
    <div class="meta">${row.emailExtracted!==null&&row.emailAdvertised!==null?escape(row.emailExtracted+" extraits sur "+row.emailAdvertised+" résultats annoncés dans le dernier email"):"Nombre de résultats du dernier email non disponible"}</div>
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
  .meta{font-size:12px;color:#9bacbf;line-height:1.6}details{border-top:1px solid #2e3b4f;padding-top:12px;color:#9eafc7;line-height:1.7}
  summary{cursor:pointer;color:#cad7eb}a{margin-top:auto;color:#a4d7ec;font-weight:650;text-decoration:none}a:hover{text-decoration:underline}
  .empty{margin-top:28px;background:#121a28;border:1px dashed #344056;padding:25px;border-radius:12px;color:#aebbcf}
  </style></head><body><main><header><div><div class="eyebrow">EDGE / RADAR / SOURCES PRIVÉES</div>
  <h1>Alertes Leboncoin<span style="color:#8dd7bf">.</span></h1>
  <p class="sub">Annonces extraites des emails Outlook et enregistrées dans D1. Ce ne sont ni des ventes conclues ni une preuve de disponibilité.</p>
  </div><span class="count">${offers.length} annonce(s) distincte(s)</span></header>
  ${offers.length?`<section class="grid" aria-label="Annonces observées">${tiles}</section>`:
    '<div class="empty">Aucune annonce importée. EDGE n’affiche pas de données fictives.</div>'}
  <p class="sub">Jusqu’à 50 annonces distinctes récentes · Consultation privée · Relevé des emails, pas vérification des offres en direct.</p>
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
        ROW_NUMBER() OVER (
          PARTITION BY o.listing_id
          ORDER BY o.observed_at DESC,o.message_id DESC
        ) AS rn
      FROM lbc_listing_observations o
      JOIN lbc_alert_messages m ON m.message_id=o.message_id
    )
    SELECT listing_id,observed_at,source_url,title,price_cents,location,
      search_name,advertised_count,extracted_count,alert_hits
    FROM ranked WHERE rn=1 ORDER BY observed_at DESC,listing_id DESC LIMIT 50`).all();
    if(!Array.isArray(data?.results)||data.results.length>50)throw Error("bad_d1_response");
    return new Response(renderOutlookOffers(data.results,{now:now()}),{status:200,headers:HEADERS});
  }catch{
    return new Response("Données momentanément indisponibles",{status:503,headers:HEADERS});
  }
}
