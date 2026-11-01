import test from 'node:test';
import assert from 'node:assert/strict';
import {DATA_BASE,PUBLIC_SCHEMAS,loadCapture,sha256,freshness,quoteState,productState,captureSummary,safeUrl,potentialBaseline} from '../assets/edge-data.mjs';
const AT=Date.parse('2026-11-01T10:00:00Z');
const source=(updates={})=>({seller:'Retrailer',source_url:'https://example.com/offer',status:'OK',usable_current_quote:true,displayed_price_eur:'129.95',availability:'IN_STOCK',observed_at:'2026-11-01T09:00:00Z',...updates});
async function fixtures(){
 const docs=Object.fromEntries(Object.entries(PUBLIC_SCHEMAS).map(([k,schema])=>[k,{schema}]));
 Object.assign(docs['report.json'],{status:'PARTIAL',observed_at:'2026-11-01T09:00:00Z',observations:[{status:'FAILED'}]});
 docs['retail_source_context.json'].products=[{product_id:'lego_75639',sources:[source()]}];
 Object.assign(docs['mri_cases.json'],{cases:[],measured_publication_reaction_windows:0});
 docs['collection_coverage.json'].missed_targets=[];
 Object.assign(docs['forecast_evaluations.json'],{metrics:[],evaluations:[]});
 const pointer={schema:'edge.public.live_capture.v1',snapshot_id:'123-1',observed_at:docs['report.json'].observed_at,status:'PARTIAL',files:{}};
 const bytes={};for(const [name,doc]of Object.entries(docs)){bytes[name]=new TextEncoder().encode(JSON.stringify(doc));pointer.files[name]={path:'snapshots/123-1/'+name,sha256:await sha256(bytes[name])};}
 const calls=[];const fetchImpl=async url=>{calls.push(url);if(url.startsWith(DATA_BASE+'latest.json?'))return new Response(JSON.stringify(pointer));const name=Object.keys(bytes).find(n=>url===DATA_BASE+'snapshots/123-1/'+n);return name?new Response(bytes[name]):new Response('',{status:404});};
 return {docs,pointer,bytes,calls,fetchImpl};
}

test('live capture uses one immutable snapshot with verified checksums',async()=>{const f=await fixtures(),c=await loadCapture({fetchImpl:f.fetchImpl});assert.equal(c.market.status,'PARTIAL');assert.equal(c.pointer.snapshot_id,'123-1');assert.equal(f.calls.length,6);assert.ok(f.calls.every(u=>!u.includes('radar.json')));});
test('network failure remains unknown and never falls back to old radar data',async()=>{await assert.rejects(loadCapture({fetchImpl:async()=>new Response('',{status:503})}),/503/);});
test('a changed archive body fails closed',async()=>{const f=await fixtures();f.bytes['report.json']=new TextEncoder().encode('{}');await assert.rejects(loadCapture({fetchImpl:f.fetchImpl}),/intégrité/);});
test('pointer cannot redirect data requests outside the immutable snapshot',async()=>{const f=await fixtures();f.pointer.files['report.json'].path='https://evil.example/report.json';await assert.rejects(loadCapture({fetchImpl:f.fetchImpl}),/archive non valide/);assert.ok(f.calls.every(u=>u.startsWith(DATA_BASE)));});
test('a valid checksum does not excuse an inconsistent capture date',async()=>{const f=await fixtures();f.pointer.observed_at='2026-10-12T10:00:00Z';await assert.rejects(loadCapture({fetchImpl:f.fetchImpl}),/incohérente/);});
test('freshness distinguishes delay, expired data, future and invalid dates',()=>{assert.equal(freshness('2026-11-01T09:00:00Z',AT).kind,'RECENT');assert.equal(freshness('2026-11-01T01:00:00Z',AT).kind,'DELAYED');assert.equal(freshness('2026-10-12T10:00:00Z',AT).kind,'STALE');assert.equal(freshness('2026-11-02T10:00:00Z',AT).kind,'UNKNOWN');assert.equal(freshness('bad',AT).kind,'UNKNOWN');});
test('failed or stale source does not become a current price or stockout',()=>{for(const s of [source({status:'FAILED',error:'HTTP Error 403'}),source({observed_at:'2026-10-12T10:00:00Z'}),source({displayed_price_eur:'NaN'}),source({displayed_price_eur:null})]){const q=quoteState(s,AT);assert.equal(q.usable,false);assert.equal(q.price,null);assert.equal(q.availability,'UNKNOWN');}});
test('cheaper stockout does not become an available purchase floor or resale margin',()=>{const p=productState({sources:[source(),source({seller:'Other',displayed_price_eur:'103.99',availability:'OUT_OF_STOCK'})]},AT);assert.equal(p.floor,129.95);assert.equal(p.spread,null);assert.equal(p.label,'Disponibilité mixte');});
test('actual in-stock price spread is computed from available source quotes',()=>{const p=productState({sources:[source(),source({seller:'Other',displayed_price_eur:'103.99'})]},AT);assert.ok(Math.abs(p.spread-25.96)<1e-10);assert.equal(p.floor,103.99);});
test('partial capture and zero scores never become a CASH or buy decision',async()=>{const f=await fixtures(),c=await loadCapture({fetchImpl:f.fetchImpl}),s=captureSummary(c,AT);assert.equal(s.status,'PARTIAL');assert.equal(s.financialDecision,'NOT_ESTABLISHED');assert.equal(s.scoredForecasts,0);assert.equal(s.currentQuotes,1);assert.equal(s.sourceFailures,1);});
test('unsafe external links cannot execute or disclose embedded credentials',()=>{assert.equal(safeUrl('javascript:alert(1)'),null);assert.equal(safeUrl('data:text/html,x'),null);assert.equal(safeUrl('https://user:pass@example.com'),null);assert.equal(safeUrl('https://example.com/offer'),'https://example.com/offer');});

test('mutable pointer is cache-busted while archive files retain immutable URLs',async()=>{const f=await fixtures();await loadCapture({fetchImpl:f.fetchImpl});assert.match(f.calls[0],/latest\.json\?v=\d+$/);assert.ok(f.calls.slice(1).every(url=>!url.includes('?')));});


test('future-event preparation expires without waiting for a new capture',()=>{
 const s={has_recent_potential_baseline:true,latest_valid_evidence:{observed_at:'2026-10-31T10:00:00Z'},potential_baseline_expires_at:'2026-11-01T10:00:00Z'};
 assert.equal(potentialBaseline(s,AT),true);
 assert.equal(potentialBaseline(s,AT+1),false);
 assert.equal(potentialBaseline({...s,has_recent_potential_baseline:false},AT),false);
 assert.equal(potentialBaseline({...s,potential_baseline_expires_at:'2027-11-01T10:00:00Z'},AT),false);
 assert.equal(potentialBaseline({...s,latest_valid_evidence:{observed_at:'2026-11-02T10:00:00Z'}},AT),false);
 assert.equal(potentialBaseline({},AT),false);
});
