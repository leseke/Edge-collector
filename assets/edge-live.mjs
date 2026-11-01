import {loadCapture,captureSummary,productState,quoteState,euro,dateText,safeUrl} from './edge-data.mjs';
const content=document.getElementById('content'),status=document.getElementById('capture-status'),refreshButton=document.getElementById('refresh');
const isMri=document.body.dataset.view==='mri';
let capture=null,loading=false,lastLoaded=0,search='';
const stockLabels={IN_STOCK:'En stock',OUT_OF_STOCK:'En rupture',UNKNOWN:'Inconnu',PREORDER:'Précommande',BACKORDER:'Sur commande',DISCONTINUED:'Arrêté',COMING_SOON:'À venir'};
const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=String(text);return n;};
function link(text,url,cls){const safe=safeUrl(url);if(!safe)return el('span',cls,text);const a=el('a',cls,text);a.href=safe;a.target='_blank';a.rel='noopener noreferrer';return a;}
function productName(id){return capture.market.observations.find(r=>r.product_id===id&&r.status==='OK'&&r.product_name)?.product_name||id.replace('lego_','LEGO ').replaceAll('_',' ');}
function showStatus(error){
 status.replaceChildren();
 if(!capture){status.className='notice bad';status.append(el('strong',null,'Les données sont momentanément indisponibles.'),el('p',null,'Réessaie dans quelques instants. Aucun prix ni stock ne peut être confirmé pour le moment.'));return;}
 const s=captureSummary(capture),stale=s.age.kind!=='RECENT';
 const label=error?'Actualisation indisponible':s.age.kind==='STALE'?'Prix à actualiser':s.age.kind==='DELAYED'?'Mise à jour en retard':s.age.kind==='UNKNOWN'?'Date non confirmée':s.status==='OK'?'Données à jour':s.status==='PARTIAL'?'Données partielles':s.status==='EMPTY'?'Aucune offre disponible':'Données indisponibles';
 status.className='notice '+(error||s.status==='FAILED'||s.age.kind==='STALE'||s.age.kind==='UNKNOWN'?'bad':s.status==='OK'&&!stale?'good':'');
 status.append(el('span','pill '+(s.status==='OK'&&!error&&!stale?'ok':'warn'),label),el('p','meta','Dernière mise à jour : '+dateText(capture.market.observed_at)+' · heure de Paris'));
 if(s.status==='PARTIAL')status.append(el('small',null,'Certaines offres ne peuvent pas être confirmées. Consulte la date et la disponibilité de chaque vendeur.'));
 if(error)status.append(el('p',null,'Les dernières informations disponibles restent affichées avec leur date. Réessaie dans quelques instants.'));
 if(stale)status.append(el('p',null,s.age.kind==='STALE'?'Les prix de plus de 24 heures ne sont plus affichés comme actuels.':'Vérifie la date des prix avant de comparer les offres.'));
}
function stats(items){const grid=el('section','stats');grid.setAttribute('aria-label','Vue d’ensemble du marché');for(const [value,label]of items){const card=el('div','stat');card.append(el('div','number',value),el('div','label',label));grid.append(card);}return grid;}
function sourceRow(source){
 const state=quoteState(source),row=el('div','seller');
 row.append(link(source.seller,source.source_url),el('div',state.usable?'price':'unknown-price',state.usable?euro(state.price):state.age.kind==='STALE'?'Prix à actualiser':'Prix indisponible'));
 row.append(el('div','seller-state '+(state.availability==='IN_STOCK'?'stock-in':state.availability==='OUT_OF_STOCK'?'stock-out':''),stockLabels[state.availability]||'Stock non établi'));
 row.append(el('div','seller-time','Relevé : '+dateText(source.observed_at)));
 if(source.seller_reliability_reviewed===false)row.append(el('small','seller-time','Fiabilité du vendeur non évaluée par EDGE.'));
 if(source.shipping_to_france_verified===false)row.append(el('small','seller-time','Livraison en France non confirmée.'));
 return row;
}
function makeProduct(product){
 const state=productState(product),card=el('article','card'),top=el('div','card-top'),heading=el('div');
 heading.append(el('div','ref',product.product_id.replace('lego_','LEGO ')),el('h3',null,productName(product.product_id)));
 top.append(heading,el('span','pill '+(state.inStock?'ok':state.outOfStock?'warn':''),state.validCount+' offre'+(state.validCount>1?'s':'')+' vérifiée'+(state.validCount>1?'s':'')));
 card.append(top,el('p','context',state.label));
 for(const {source}of state.sources)card.append(sourceRow(source));
 if(state.spread!==null)card.append(el('p','spread','Écart entre les prix en stock : '+euro(state.spread)+' · hors livraison'));
 return card;
}
function sectionHeading(title,sub){const head=el('div','section-head');const copy=el('div');copy.append(el('h2',null,title));if(sub)copy.append(el('small',null,sub));head.append(copy);return head;}
function analysisLimits(){
 const box=el('details','method');box.append(el('summary',null,'Comment interpréter ces informations ?'));
 box.append(el('p',null,'Les prix affichés et les disponibilités sont ceux annoncés par les vendeurs à la date indiquée. Une rupture chez un vendeur ne prouve pas une pénurie générale.'),el('p',null,'Les frais de livraison et les ventes réellement conclues ne sont pas confirmés. Un écart entre deux offres ne correspond pas à un bénéfice de revente.'),el('p',null,'Les données disponibles ne permettent pas encore de fournir une probabilité de gain fiable. Les prix affichés ne suffisent pas à recommander un achat.'));
 return box;
}
function budget(){
 const box=el('details','method');box.append(el('summary',null,'Mon budget personnel — sur cet appareil'),el('p',null,'Ce montant n’est pas relié aux achats engagés. Il ne sert pas à calculer une trésorerie disponible ni à filtrer la découverte.'));
 const form=el('form','budget-form'),input=el('input'),label=el('label',null,'Montant en euros');input.id='local-budget';input.type='number';input.min='0';input.step='0.01';input.placeholder='Non renseigné';label.htmlFor=input.id;
 try{const saved=localStorage.getItem('edge_research_budget')??localStorage.getItem('edge_sim_capital');if(saved!==null&&Number.isFinite(Number(saved))&&Number(saved)>=0)input.value=saved;}catch{}
 const button=el('button',null,'Enregistrer'),message=el('small');button.type='submit';message.setAttribute('role','status');
 form.append(label,input,button,message);form.addEventListener('submit',event=>{event.preventDefault();const value=input.value;if(value!==''&&(!Number.isFinite(Number(value))||Number(value)<0)){message.textContent='Renseigne un montant positif ou nul.';return;}try{if(value===''){localStorage.removeItem('edge_research_budget');localStorage.removeItem('edge_sim_capital');}else localStorage.setItem('edge_research_budget',value);message.textContent='Enregistré uniquement sur cet appareil.';}catch{message.textContent='L’enregistrement local est indisponible.';}});box.append(form);return box;
}
function renderDashboard(){
 const s=captureSummary(capture);content.append(stats([[s.currentQuotes,'Offres vérifiées'],[s.observedProducts,'Produits suivis'],[s.multiSourceProducts,'Comparaisons entre vendeurs'],[s.linkedCases,'Produits avec une actualité']]));
 const heading=sectionHeading('Prix et disponibilités','Offres observées · frais de livraison non vérifiés'),input=el('input','search');input.type='search';input.placeholder='Référence, produit ou vendeur';input.setAttribute('aria-label','Filtrer les produits ou vendeurs');input.value=search;heading.append(input);content.append(heading);
 const list=el('section','cards');list.setAttribute('aria-label','Produits observés');content.append(list);
 const draw=()=>{list.replaceChildren();const needle=search.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();const products=[...capture.context.products].sort((a,b)=>productState(b).validCount-productState(a).validCount||a.product_id.localeCompare(b.product_id));
 for(const product of products){const text=(product.product_id+' '+productName(product.product_id)+' '+product.sources.map(s=>s.seller).join(' ')).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();if(text.includes(needle))list.append(makeProduct(product));}if(!list.children.length)list.append(el('p','empty','Aucun produit ne correspond au filtre.'));};
 input.addEventListener('input',()=>{search=input.value;draw();});draw();content.append(analysisLimits(),budget());
}
function makeCase(c){
 const card=el('article','card case');card.append(el('div','ref',c.product_id.replace('lego_','LEGO ')),el('h2',null,productName(c.product_id)));
 if(c.announced_release){const r=c.announced_release,release=el('div','publication');release.append(el('strong',null,'Sortie grand public annoncée : '+new Intl.DateTimeFormat('fr-FR',{dateStyle:'long',timeZone:'UTC'}).format(new Date(r.date+'T00:00:00Z'))),link('Annonce du fabricant',r.source_url),el('small',null,'La disponibilité à cette date reste à vérifier auprès des vendeurs.'));card.append(release);}
 const articles=c.announced_release?c.publication_evidence.filter(p=>p.source_url!==c.announced_release.source_url):c.publication_evidence;
 const articleBox=articles.length>2?el('details','publication'):card;
 if(articleBox!==card)articleBox.append(el('summary',null,'Articles associés ('+articles.length+')'));
 for(const p of articles){const pub=el('div','publication');pub.append(link(p.title,p.source_url),el('small',null,'Date déclarée : '+dateText(p.published_at)+' · '+(p.source_role==='MANUFACTURER'?'Fabricant':'Média spécialisé')));articleBox.append(pub);}
 if(articleBox!==card)card.append(articleBox);
 if(!c.publication_evidence.length)card.append(el('p','muted','Comparaison des offres disponibles.'));
 const sources=el('div','sources');for(const source of c.retail_sources){const wrap=el('section');wrap.append(sourceRow(source.current_quote));
 const first=source.first_observation,last=source.latest_observation,period=el('div','period');period.append(el('div',null,'Premier relevé : '+dateText(first.observed_at)+' · '+euro(Number(first.price))),el('div',null,'Dernier relevé : '+dateText(last.observed_at)));
 const variation=source.displayed_price_change_since_first_capture_pct;
 period.append(el('div',null,variation===null?'Historique encore insuffisant pour mesurer une variation.':'Variation du prix affiché sur la période : '+new Intl.NumberFormat('fr-FR',{maximumFractionDigits:2,signDisplay:'exceptZero'}).format(Number(variation))+' %'));
 wrap.append(period);sources.append(wrap);}card.append(sources);
 if(c.announced_release){card.append(el('p','reaction','Les prix affichés sont suivis autour de la sortie annoncée. L’effet de cette sortie sur le marché n’est pas encore établi.'));}
 else if(c.publication_evidence.length){const note=el('div','reaction');note.append(el('strong',null,c.measured_publication_reaction_windows?'Comparaison des prix avant et après publication disponible':'Effet de cette actualité : non établi'));
 const noBaseline=c.publication_reaction_measurements.some(m=>m.status==='NO_PRE_EVENT_BASELINE');note.append(el('p',null,noBaseline?'Il manque un relevé avant publication. Les variations depuis la première capture ne mesurent pas l’effet de cet article.':'Une association chronologique ne démontre pas que la publication a causé une évolution.'));
 card.append(note);}
 card.append(el('p','warning-copy','Prix de revente et bénéfice potentiel : non évalués.'));return card;
}
function renderMri(){
 const s=captureSummary(capture);content.append(stats([[s.linkedCases,'Produits avec une actualité'],[s.multiSourceProducts,'Comparaisons entre vendeurs'],[s.measuredReactions,'Comparaisons avant / après'],['Non disponibles','Prix de ventes conclues']]));
 const linked=capture.cases.cases.filter(c=>c.publication_evidence.length),others=capture.cases.cases.filter(c=>!c.publication_evidence.length);
 content.append(sectionHeading('Actualités et évolution des prix','Les publications à suivre et les variations réellement observées.'));
 if(!linked.length)content.append(el('p','empty','Aucune actualité associée aux produits comparés pour le moment.'));
 for(const c of linked)content.append(makeCase(c));
 if(others.length){content.append(sectionHeading('Autres produits suivis'));for(const c of others)content.append(makeCase(c));}
 content.append(analysisLimits());
}
function render(error){showStatus(error);content.replaceChildren();content.setAttribute('aria-busy','false');if(!capture)return;if(isMri)renderMri();else renderDashboard();}
async function refresh(){if(loading)return;loading=true;refreshButton.disabled=true;refreshButton.textContent='Lecture…';const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),20000);
 try{capture=await loadCapture({signal:controller.signal});lastLoaded=Date.now();render();}
 catch{controller.abort();render(true);}
 finally{clearTimeout(timer);loading=false;refreshButton.disabled=false;refreshButton.textContent='Actualiser';}}
refreshButton.addEventListener('click',refresh);document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&Date.now()-lastLoaded>60000)refresh();});setInterval(()=>{if(document.visibilityState==='visible')refresh();},15*60*1000);
refresh();
