import {loadCapture,captureSummary,productState,quoteState,euro,dateText,safeUrl,potentialBaseline} from './edge-data.mjs';
const content=document.getElementById('content'),status=document.getElementById('capture-status'),refreshButton=document.getElementById('refresh');
const isMri=document.body.dataset.view==='mri';
let capture=null,loading=false,lastLoaded=0,search='';
const stockLabels={IN_STOCK:'En stock',OUT_OF_STOCK:'En rupture',UNKNOWN:'Inconnu',PREORDER:'Précommande',BACKORDER:'Sur commande',DISCONTINUED:'Arrêté'};
const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=String(text);return n;};
function link(text,url,cls){const safe=safeUrl(url);if(!safe)return el('span',cls,text);const a=el('a',cls,text);a.href=safe;a.target='_blank';a.rel='noopener noreferrer';return a;}
function productName(id){return capture.market.observations.find(r=>r.product_id===id&&r.status==='OK'&&r.product_name)?.product_name||id.replace('lego_','LEGO ').replaceAll('_',' ');}
function archiveLink(file){return 'https://github.com/leseke/Edge-collector/blob/edge/commercial-history/snapshots/'+capture.pointer.snapshot_id+'/'+file;}
function showStatus(error){
 status.replaceChildren();
 if(!capture){status.className='notice bad';status.append(el('strong',null,'Lecture de la collecte impossible'),el('p',null,error||'Aucune capture vérifiée n’est disponible.'),el('small',null,'Aucun prix, état de stock ou statut financier n’est déduit sans ces données.'));return;}
 const s=captureSummary(capture),stale=s.age.kind!=='RECENT';
 const label=error?'ACTUALISATION IMPOSSIBLE':s.age.kind==='STALE'?'CAPTURE PÉRIMÉE':s.age.kind==='DELAYED'?'COLLECTE EN RETARD':s.age.kind==='UNKNOWN'?'DATE NON VÉRIFIÉE':s.status==='OK'?'COLLECTE VÉRIFIÉE':s.status==='PARTIAL'?'COLLECTE PARTIELLE':s.status==='EMPTY'?'COLLECTE VIDE':'COLLECTE EN ÉCHEC';
 status.className='notice '+(error||s.status==='FAILED'||s.age.kind==='STALE'||s.age.kind==='UNKNOWN'?'bad':s.status==='OK'&&!stale?'good':'');
 status.append(el('span','pill '+(s.status==='OK'&&!error&&!stale?'ok':'warn'),label),el('strong',null,`${s.currentQuotes} relevés commerciaux actuellement vérifiés · ${s.sourceFailures} sources en échec`),el('p','meta','Capture du '+dateText(capture.market.observed_at)+' · heure de Paris'));
 if(error)status.append(el('p',null,'La dernière capture vérifiée reste affichée. '+error));
 if(stale)status.append(el('p',null,s.age.kind==='STALE'?'Les prix de plus de 24 heures sont masqués comme périmés.':'La cadence visée est de trois heures. La date des relevés reste la référence.'));
 status.append(el('small',null,'Décision d’achat : non établie. Trésorerie disponible : non calculée.'));
}
function stats(items){const grid=el('section','stats');grid.setAttribute('aria-label','État de la capture');for(const [value,label]of items){const card=el('div','stat');card.append(el('div','number',value),el('div','label',label));grid.append(card);}return grid;}
function sourceRow(source){
 const state=quoteState(source),row=el('div','seller');
 row.append(link(source.seller,source.source_url),el('div',state.usable?'price':'unknown-price',state.usable?euro(state.price):state.reason));
 row.append(el('div','seller-state '+(state.availability==='IN_STOCK'?'stock-in':state.availability==='OUT_OF_STOCK'?'stock-out':''),stockLabels[state.availability]||'Stock non établi'));
 row.append(el('div','seller-time','Relevé : '+dateText(source.observed_at)));return row;
}
function makeProduct(product){
 const state=productState(product),card=el('article','card'),top=el('div','card-top'),heading=el('div');
 heading.append(el('div','ref',product.product_id.replace('lego_','LEGO ')),el('h3',null,productName(product.product_id)));
 top.append(heading,el('span','pill '+(state.inStock?'ok':state.outOfStock?'warn':''),state.validCount+' source'+(state.validCount>1?'s':'')));
 card.append(top,el('p','context',state.label));
 for(const {source}of state.sources)card.append(sourceRow(source));
 if(state.spread!==null)card.append(el('p','spread','Écart entre les prix en stock : '+euro(state.spread)+' · hors livraison'));
 return card;
}
function sectionHeading(title,sub){const head=el('div','section-head');const copy=el('div');copy.append(el('h2',null,title));if(sub)copy.append(el('small',null,sub));head.append(copy);return head;}
function quality(){
 const s=captureSummary(capture),wrap=el('section','quality'),incidents=el('article','card');
 incidents.append(el('h3',null,'Continuité de collecte'),el('div','number',s.missedWindows),el('small',null,'fenêtre'+(s.missedWindows>1?'s':'')+' cible'+(s.missedWindows>1?'s':'')+' manquante'+(s.missedWindows>1?'s':'')+' dans l’historique'));
 const reasons={NO_ARCHIVED_CAPTURE_RUN_IN_TARGET_WINDOW:'Aucun passage archivé dans la fenêtre cible.',SOURCE_REQUESTS_FAILED_IN_TARGET_WINDOW:'La source a échoué pendant la fenêtre cible.',SOURCE_NOT_OBSERVED_IN_ARCHIVED_TARGET_RUNS:'La source était absente des passages archivés.',FOLLOWUP_AND_SOURCE_EVIDENCE_DISAGREE:'Les captures et le suivi demandent une vérification.'};
 for(const i of capture.coverage.missed_targets.slice(0,4)){const item=el('div','incident');item.append(el('strong',null,i.product_id.replace('lego_','LEGO ')+' · J+'+i.horizon_hours/24),el('p',null,reasons[i.diagnosis]||'Capture non exploitable.'),el('small',null,dateText(i.window_start)+' → '+dateText(i.window_end)));if(Number.isFinite(i.successful_capture_gap_hours))item.append(el('small',null,'Intervalle constaté entre relevés réussis : '+new Intl.NumberFormat('fr-FR',{maximumFractionDigits:1}).format(i.successful_capture_gap_hours)+' h'));incidents.append(item);}
 if(!s.missedWindows)incidents.append(el('p','muted','Aucune fenêtre cible manquante constatée dans ce rapport.'));
 incidents.append(link('Voir le diagnostic archivé',archiveLink('coverage_report.md')));
 const forecasts=el('article','card');forecasts.append(el('h3',null,'Validation des estimations'),el('div','number',s.scoredForecasts),el('small',null,'prévisions évaluées en conditions prospectives'),el('p','warning-copy','Les abstentions et les captures manquantes sont exclues des scores. Calibration et avantage prédictif : non établis.'));
 for(const f of capture.forecasts.evaluations.slice(-6)){const item=el('div','forecast-row');item.append(el('strong',null,'J+'+f.horizon_hours/24));
 const label=f.estimate_status==='ESTIMATE'?'Estimation enregistrée':'Abstention : données insuffisantes';item.append(el('span',null,label));
 const outcome={PENDING_HORIZON:'Échéance à venir',AWAITING_CAPTURE:'Capture attendue',MISSING_WINDOW_OBSERVATION:'Capture cible manquante',MEASURED:'Résultat observé',EVENT_EVIDENCE_UNAVAILABLE:'Preuves de l’événement indisponibles'};
 item.append(el('small',null,(outcome[f.outcome_status]||f.outcome_status)+' · '+dateText(f.target_at)));
 if(f.registration_timing==='LATE_REGISTRATION')item.append(el('small',null,'Inscription tardive, exclue des scores prospectifs.'));forecasts.append(item);}
 forecasts.append(link('Voir le registre daté',archiveLink('forecast_report.md')));wrap.append(incidents,forecasts,preparation());return wrap;
}
function preparation(){
 const box=el('article','card preparation'),data=capture.coverage.event_preparation;
 box.append(el('h3',null,'Préparation aux prochains événements'));
 if(!data){box.append(el('p','muted','Diagnostic absent de cette ancienne capture.'));return box;}
 const products=data.products,now=Date.now(),count=products.filter(p=>p.sources.some(s=>potentialBaseline(s,now))).length;
 box.append(el('div','number',count),el('small',null,'produits avec un point de départ encore récent'),el('p',null,'Un relevé de moins de 24 h pourra servir de comparaison si un nouvel événement survient. Ce compteur ne mesure ni une opportunité ni une probabilité de gain.'),el('small',null,'Historique évalué : '+dateText(data.assessed_at)+'. Les expirations sont revérifiées à l’affichage.'));
 const labels={NO_VALID_CAPTURE:'Aucune preuve exploitable',STALE_HISTORY:'Historique trop ancien',COLLECTION_INTERRUPTED:'Collecte interrompue à cette capture',SINGLE_RECENT_CAPTURE:'Un seul relevé récent',GAPPED_RECENT_SERIES:'Historique récent avec un intervalle de plus de 6 h',RECENT_SERIES:'Plusieurs relevés récents'};
 for(const p of products){const detail=el('details'),valid=p.sources.filter(s=>potentialBaseline(s,now));detail.append(el('summary',null,p.product_id.replace('lego_','LEGO ')+' · '+new Set(valid.map(s=>s.seller)).size+' vendeur(s) avec un point de départ récent'));
 for(const s of p.sources){const row=el('div','period');row.append(link(s.seller,s.source_url),el('div',null,labels[s.status]||'État non établi'),el('div',null,s.recent_distinct_capture_count+' capture(s) distincte(s) sur les 24 h précédant ce rapport.'));
 if(s.latest_valid_evidence)row.append(el('small',null,'Dernière preuve : '+dateText(s.latest_valid_evidence.observed_at)),el('small',null,'Point de départ utilisable jusqu’au : '+dateText(s.potential_baseline_expires_at)));
 if(!potentialBaseline(s,now))row.append(el('small','warning-copy','Aucun point de départ encore récent à cet affichage.'));
 if(s.conflicting_timestamps_excluded)row.append(el('small','warning-copy',s.conflicting_timestamps_excluded+' horodatage(s) contradictoire(s) exclu(s).'));
 detail.append(row);}box.append(detail);}
 box.append(link('Consulter les preuves et les interruptions',archiveLink('coverage_report.md')));return box;
}
function method(){const box=el('details','method');box.append(el('summary',null,'Sources, périmètre et limites'));
 box.append(el('p',null,'Les prix et stocks sont ceux déclarés par les vendeurs au moment du relevé. Une rupture sur les sources suivies ne prouve pas une pénurie générale.'),el('p',null,'Prix de ventes conclues, volumes, frais livrés et marge nette : non établis. Les comparaisons de prix affichés ne sont pas des estimations de bénéfice.'));
 const n=capture.market.coverage?.indicative_prices_ok||0;if(n)box.append(el('p',null,`${n} indications agrégées de cartes sont collectées séparément. Elles ne sont pas présentées comme des offres de produits Pokémon scellés.`));
 const audit=el('div','audit');audit.append(link('Capture et provenance',archiveLink('report.json')),link('Dossiers MRI archivés',archiveLink('mri_case_report.md')),link('Incidents de collecte',archiveLink('coverage_report.md')));box.append(audit);return box;}
function budget(){
 const box=el('details','method');box.append(el('summary',null,'Mon budget personnel — sur cet appareil'),el('p',null,'Ce montant n’est pas relié aux achats engagés. Il ne sert pas à calculer une trésorerie disponible ni à filtrer la découverte.'));
 const form=el('form','budget-form'),input=el('input'),label=el('label',null,'Montant en euros');input.id='local-budget';input.type='number';input.min='0';input.step='0.01';input.placeholder='Non renseigné';label.htmlFor=input.id;
 try{const saved=localStorage.getItem('edge_research_budget')??localStorage.getItem('edge_sim_capital');if(saved!==null&&Number.isFinite(Number(saved))&&Number(saved)>=0)input.value=saved;}catch{}
 const button=el('button',null,'Enregistrer'),message=el('small');button.type='submit';message.setAttribute('role','status');
 form.append(label,input,button,message);form.addEventListener('submit',event=>{event.preventDefault();const value=input.value;if(value!==''&&(!Number.isFinite(Number(value))||Number(value)<0)){message.textContent='Renseigne un montant positif ou nul.';return;}try{if(value===''){localStorage.removeItem('edge_research_budget');localStorage.removeItem('edge_sim_capital');}else localStorage.setItem('edge_research_budget',value);message.textContent='Enregistré uniquement sur cet appareil.';}catch{message.textContent='L’enregistrement local est indisponible.';}});box.append(form);return box;
}
function renderDashboard(){
 const s=captureSummary(capture);content.append(stats([[s.currentQuotes,'Relevés commerciaux vérifiés'],[s.observedProducts,'Produits avec un relevé récent'],[s.multiSourceProducts,'Produits comparés entre vendeurs'],[s.linkedCases,'Dossiers associés à une publication']]));
 const heading=sectionHeading('Prix et disponibilités','Offres observées · frais de livraison non vérifiés'),input=el('input','search');input.type='search';input.placeholder='Référence, produit ou vendeur';input.setAttribute('aria-label','Filtrer les produits ou vendeurs');input.value=search;heading.append(input);content.append(heading);
 const list=el('section','cards');list.setAttribute('aria-label','Produits observés');content.append(list);
 const draw=()=>{list.replaceChildren();const needle=search.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();const products=[...capture.context.products].sort((a,b)=>productState(b).validCount-productState(a).validCount||a.product_id.localeCompare(b.product_id));
 for(const product of products){const text=(product.product_id+' '+productName(product.product_id)+' '+product.sources.map(s=>s.seller).join(' ')).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();if(text.includes(needle))list.append(makeProduct(product));}if(!list.children.length)list.append(el('p','empty','Aucun produit ne correspond au filtre.'));};
 input.addEventListener('input',()=>{search=input.value;draw();});draw();content.append(sectionHeading('Ce qui est mesurable'),quality(),method(),budget());
}
function makeCase(c){
 const card=el('article','card case');card.append(el('div','ref',c.product_id.replace('lego_','LEGO ')),el('h2',null,productName(c.product_id)));
 if(c.candidate_first_observed_at)card.append(el('small',null,'Découvert par EDGE : '+dateText(c.candidate_first_observed_at)));
 for(const p of c.publication_evidence){const pub=el('div','publication');pub.append(link(p.title,p.source_url),el('small',null,'Date déclarée : '+dateText(p.published_at)+' · '+(p.source_role==='MANUFACTURER'?'Fabricant':'Média spécialisé')),el('small',null,p.reference_in_title?'Référence présente dans le titre.':'Référence citée dans le contenu.'));card.append(pub);}
 if(!c.publication_evidence.length)card.append(el('p','muted','Comparaison témoin : aucune publication de découverte associée.'));
 const sources=el('div','sources');for(const source of c.retail_sources){const wrap=el('section');wrap.append(sourceRow(source.current_quote));
 const first=source.first_observation,last=source.latest_observation,period=el('div','period');period.append(el('div',null,'Premier relevé : '+dateText(first.observed_at)+' · '+euro(Number(first.price))),el('div',null,'Dernier relevé : '+dateText(last.observed_at)));
 const variation=source.displayed_price_change_since_first_capture_pct;
 period.append(el('div',null,variation===null?'Variation non mesurée : premier relevé.':'Variation pendant la période observée : '+new Intl.NumberFormat('fr-FR',{maximumFractionDigits:2,signDisplay:'exceptZero'}).format(Number(variation))+' %'));
 wrap.append(period);sources.append(wrap);}card.append(sources);
 if(c.publication_evidence.length){const note=el('div','reaction');note.append(el('strong',null,c.measured_publication_reaction_windows?`${c.measured_publication_reaction_windows} fenêtre(s) descriptive(s) mesurée(s)`:'Réaction à la publication : non mesurable'));
 const noBaseline=c.publication_reaction_measurements.some(m=>m.status==='NO_PRE_EVENT_BASELINE');note.append(el('p',null,noBaseline?'Il manque un relevé avant publication. Les variations depuis la première capture ne mesurent pas l’effet de cet article.':'Une association chronologique ne démontre pas que la publication a causé une évolution.'));
 for(const m of c.publication_reaction_measurements){const a=m.baseline_audit;if(!a)continue;const reason=a.status==='AVAILABLE'?'Relevé antérieur utilisable (moins de 24 h).':a.status==='STALE_PRIOR_CAPTURE'?'Dernier relevé antérieur trop ancien (plus de 24 h).':'Aucune capture strictement antérieure à la publication.';const detail=el('details');detail.append(el('summary',null,(m.seller||'Source')+' — '+reason),el('p',null,'Premier relevé archivé : '+dateText(a.first_capture_at)));if(a.latest_prior_observation){const p=a.latest_prior_observation;detail.append(el('p',null,'Dernier relevé avant publication : '+dateText(p.observed_at)),el('small',null,'Preuve SHA-256 : '+p.body_sha256));}detail.append(el('small',null,'Les relevés simultanés à la publication sont exclus du point de départ.'));note.append(detail);}
 card.append(note);}
 card.append(el('p','warning-copy','Ventes conclues, liquidité et marge nette : non établies. Décision d’achat : non établie.'));return card;
}
function renderMri(){const s=captureSummary(capture);content.append(stats([[s.linkedCases,'Dossiers avec publication'],[s.multiSourceProducts,'Produits suivis chez plusieurs vendeurs'],[s.measuredReactions,'Fenêtres de réaction mesurées'],[s.scoredForecasts,'Prévisions prospectives évaluées']]));
 const linked=capture.cases.cases.filter(c=>c.publication_evidence.length),controls=capture.cases.cases.filter(c=>!c.publication_evidence.length);
 content.append(sectionHeading('Publications et suivi de marché','Les faits disponibles et les limites de mesure pour chaque dossier.'));if(!linked.length)content.append(el('p','empty','Aucun dossier avec publication et plusieurs vendeurs vérifiés dans cette capture.'));for(const c of linked)content.append(makeCase(c));
 if(controls.length){content.append(sectionHeading('Comparaisons témoins'));for(const c of controls)content.append(makeCase(c));}content.append(sectionHeading('Incidents et estimations datées'),quality(),method());
}
function render(error){showStatus(error);content.replaceChildren();content.setAttribute('aria-busy','false');if(!capture)return;if(isMri)renderMri();else renderDashboard();}
async function refresh(){if(loading)return;loading=true;refreshButton.disabled=true;refreshButton.textContent='Lecture…';const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),20000);
 try{capture=await loadCapture({signal:controller.signal});lastLoaded=Date.now();render();}
 catch(error){controller.abort();render(error.name==='AbortError'?'Délai de lecture dépassé.':error.message);}
 finally{clearTimeout(timer);loading=false;refreshButton.disabled=false;refreshButton.textContent='Actualiser';}}
refreshButton.addEventListener('click',refresh);document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&Date.now()-lastLoaded>60000)refresh();});setInterval(()=>{if(document.visibilityState==='visible')refresh();},15*60*1000);
refresh();
