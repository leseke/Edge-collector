export const DATA_BASE='https://raw.githubusercontent.com/leseke/Edge-collector/edge/commercial-history/';
export const PUBLIC_SCHEMAS={
 'report.json':'edge.commercial.snapshot.v1',
 'retail_source_context.json':'edge.mri.retail_source_context.v1',
 'mri_cases.json':'edge.mri.multi_source_cases.v1',
 'collection_coverage.json':'edge.mri.collection_coverage.v1',
 'forecast_evaluations.json':'edge.mri.prospective_followup.v1'
};
export const timestamp=value=>typeof value==='string'&&Number.isFinite(Date.parse(value))?Date.parse(value):null;
export function potentialBaseline(source,now=Date.now()){
 const observed=timestamp(source.latest_valid_evidence?.observed_at),expires=timestamp(source.potential_baseline_expires_at);
 return source.has_recent_potential_baseline===true&&observed!==null&&expires!==null&&observed<=now&&now<=expires&&expires-observed===86400000;
}
export function freshness(value,now=Date.now()){
 const stamp=timestamp(value);
 if(stamp===null||stamp>now+300000)return {kind:'UNKNOWN',label:'Date non vérifiée',hours:null};
 const hours=Math.max(0,(now-stamp)/3600000);
 return {kind:hours>24?'STALE':hours>6?'DELAYED':'RECENT',label:hours>24?'Capture périmée':hours>6?'Collecte en retard':'Capture récente',hours};
}
export function quoteState(source,now=Date.now()){
 const age=freshness(source.observed_at,now),price=Number(source.displayed_price_eur);
 const usable=source.status==='OK'&&source.usable_current_quote===true&&source.displayed_price_eur!==null&&source.displayed_price_eur!==''&&Number.isFinite(price)&&price>0&&age.kind!=='STALE'&&age.kind!=='UNKNOWN';
 return {usable,price:usable?price:null,availability:usable?source.availability:'UNKNOWN',age,
  reason:usable?null:source.status!=='OK'?(String(source.error||'').includes('403')?'Accès refusé':String(source.error||'').toLowerCase().includes('timed out')?'Délai dépassé':'Offre non vérifiée'):age.kind==='STALE'?'Relevé périmé':'Prix non vérifié'};
}
export function safeUrl(value){try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password?u.href:null;}catch{return null;}}
export const euro=value=>Number.isFinite(value)?new Intl.NumberFormat('fr-FR',{style:'currency',currency:'EUR'}).format(value):'Non établi';
export function dateText(value){return timestamp(value)===null?'Date non établie':new Intl.DateTimeFormat('fr-FR',{timeZone:'Europe/Paris',dateStyle:'medium',timeStyle:'short'}).format(new Date(value));}
export function productState(product,now=Date.now()){
 const sources=product.sources.map(source=>({source,state:quoteState(source,now)}));
 const valid=sources.filter(s=>s.state.usable),available=valid.filter(s=>s.state.availability==='IN_STOCK'),out=valid.filter(s=>s.state.availability==='OUT_OF_STOCK');
 const prices=available.map(s=>s.state.price),upcoming=valid.filter(s=>s.state.availability==='COMING_SOON');
 return {sources,validCount:valid.length,inStock:available.length,outOfStock:out.length,
  floor:prices.length?Math.min(...prices):null,spread:prices.length>=2?Math.max(...prices)-Math.min(...prices):null,
  label:available.length&&out.length?'Disponibilité mixte':out.length?'Rupture sur les sources observées':available.length?'En stock sur les sources observées':upcoming.length?'Commercialisation à venir':'Disponibilité non établie'};
}
export function captureSummary(capture,now=Date.now()){
 const states=capture.context.products.map(p=>productState(p,now));
 const sourceFailures=capture.market.observations.filter(r=>r.status==='FAILED').length;
 return {age:freshness(capture.market.observed_at,now),status:capture.market.status,
  currentQuotes:states.reduce((n,p)=>n+p.validCount,0),observedProducts:states.filter(p=>p.validCount>0).length,
  multiSourceProducts:states.filter(p=>p.validCount>=2).length,sourceFailures,
  missedWindows:capture.coverage.missed_targets.length,
  linkedCases:capture.cases.cases.filter(c=>c.publication_evidence.length>0).length,
  measuredReactions:capture.cases.measured_publication_reaction_windows,
  scoredForecasts:capture.forecasts.metrics.reduce((n,m)=>n+m.scored_count,0),
  financialDecision:'NOT_ESTABLISHED'};
}
async function fetchBytes(url,fetchImpl,signal){
 const response=await fetchImpl(url,{cache:'no-store',signal});
 if(!response.ok)throw Error('Lecture du flux impossible ('+response.status+').');
 const declared=Number(response.headers?.get?.('content-length')||0);
 if(declared>5000000)throw Error('Archive trop volumineuse.');
 const bytes=await response.arrayBuffer();if(bytes.byteLength>5000000)throw Error('Archive trop volumineuse.');return bytes;
}
export async function sha256(bytes){return Array.from(new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256',bytes))).map(n=>n.toString(16).padStart(2,'0')).join('');}
export async function loadCapture({fetchImpl=fetch,signal}={}){
 const pointerUrl=new URL('latest.json',DATA_BASE);pointerUrl.searchParams.set('v',String(Date.now()));
 const pointer=JSON.parse(new TextDecoder().decode(await fetchBytes(pointerUrl.href,fetchImpl,signal)));
 if(pointer.schema!=='edge.public.live_capture.v1'||!/^\d+-\d+$/.test(pointer.snapshot_id)||timestamp(pointer.observed_at)===null)throw Error('Référence de capture non valide.');
 const entries=await Promise.all(Object.entries(PUBLIC_SCHEMAS).map(async([name,schema])=>{
  const file=pointer.files?.[name],path='snapshots/'+pointer.snapshot_id+'/'+name;
  if(!file||file.path!==path||!/^[a-f0-9]{64}$/.test(file.sha256))throw Error('Référence d’archive non valide.');
  const bytes=await fetchBytes(DATA_BASE+path,fetchImpl,signal);
  if(await sha256(bytes)!==file.sha256)throw Error('L’intégrité de la capture ne peut pas être vérifiée.');
  const doc=JSON.parse(new TextDecoder().decode(bytes));if(doc.schema!==schema)throw Error('Format de capture inattendu.');
  return [name,doc];
 }));
 const docs=Object.fromEntries(entries),market=docs['report.json'];
 if(market.observed_at!==pointer.observed_at||market.status!==pointer.status||!['OK','PARTIAL','FAILED','EMPTY'].includes(market.status))throw Error('Capture incohérente.');
 if(!Array.isArray(market.observations)||!Array.isArray(docs['retail_source_context.json'].products)||!Array.isArray(docs['mri_cases.json'].cases)||!Array.isArray(docs['collection_coverage.json'].missed_targets)||!Array.isArray(docs['forecast_evaluations.json'].metrics)||!Array.isArray(docs['forecast_evaluations.json'].evaluations))throw Error('Capture incomplète.');
 for(const p of docs['retail_source_context.json'].products){if(typeof p.product_id!=='string'||!Array.isArray(p.sources)||p.sources.some(s=>typeof s.seller!=='string'||typeof s.status!=='string'))throw Error('Sources commerciales incomplètes.');}
 for(const c of docs['mri_cases.json'].cases){if(typeof c.product_id!=='string'||!Array.isArray(c.publication_evidence)||!Array.isArray(c.retail_sources)||!Array.isArray(c.publication_reaction_measurements)||c.retail_sources.some(s=>!s.current_quote||!s.first_observation||!s.latest_observation))throw Error('Dossier incomplet.');}
 for(const m of docs['forecast_evaluations.json'].metrics){if(!Number.isInteger(m.scored_count)||m.scored_count<0)throw Error('Évaluation incomplète.');}
 return {pointer,market,context:docs['retail_source_context.json'],cases:docs['mri_cases.json'],coverage:docs['collection_coverage.json'],forecasts:docs['forecast_evaluations.json']};
}
