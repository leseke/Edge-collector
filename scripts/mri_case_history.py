"""Observed publication and multi-retailer dossiers without invented causal reactions."""
import argparse
import json
import re
from decimal import Decimal
from pathlib import Path
from announcement_history import timestamp
from commercial_history import now


def build(candidates, context, reports, reactions, at, primary=None):
    by_product={c['id']:c for c in candidates};cases=[]
    for product in context['products']:
        cid=product['product_id'];candidate=by_product.get(cid)
        verified={s['id']:s for s in (primary or {}).get('sources',[]) if s['status']=='VERIFIED_MATCH'}
        releases=[c for r in (primary or {}).get('reviews',[]) if r['candidate_id']==cid and r.get('current_recheck_verified')
                  for c in r.get('supported_claims',[]) if c['kind']=='ANNOUNCED_GENERAL_RELEASE' and c.get('source_id') in verified
                  and re.fullmatch(r'\d{4}-\d{2}-\d{2}',c.get('date','')) and timestamp(c['date']+'T00:00:00+00:00')]
        release=({'date':releases[0]['date'],'date_precision':'DAY','source_url':verified[releases[0]['source_id']]['source_url'],
                  'status':'MANUFACTURER_ANNOUNCEMENT_NOT_CONFIRMED_LAUNCH_HOUR'} if len(releases)==1 else None)
        if product['verified_current_seller_count']<1 or (product['verified_current_seller_count']<2 and not release):continue
        publications=candidate['evidence'] if candidate else []
        sources=[]
        for current in product['sources']:
            if not current['usable_current_quote']:continue
            rows={ (r['observed_at'],r['body_sha256']):r for report in reports for r in report['observations']
                if r.get('product_id')==cid and r.get('status')=='OK' and r.get('price_kind')=='ASKING_PRICE'
                and r.get('seller')==current['seller'] and r.get('url')==current['source_url'] and r.get('currency')=='EUR'
                and timestamp(r.get('observed_at')) and timestamp(r['observed_at'])<=timestamp(at)}
            rows=sorted(rows.values(),key=lambda r:timestamp(r['observed_at']))
            if not rows:continue
            first,last=rows[0],rows[-1]
            sources.append({'seller':current['seller'],'source_url':current['source_url'],
                'current_quote':current,'successful_capture_count':len(rows),
                'first_observation':{k:first.get(k) for k in ('id','observed_at','price','currency','availability','body_sha256')},
                'latest_observation':{k:last.get(k) for k in ('id','observed_at','price','currency','availability','body_sha256')},
                'displayed_price_change_since_first_capture_pct':str((Decimal(last['price'])/Decimal(first['price'])-1)*100) if len(rows)>=2 else None,
                'change_is_publication_effect':False})
        publication_ids={p['publication_id'] for p in publications}
        source_keys={(s['first_observation']['id'],s['source_url'],s['seller'],cid,s['first_observation']['currency']) for s in sources}
        measurements=[r for r in reactions.get('measurements',[]) if r['publication_id'] in publication_ids
                      and (r.get('observation_id'),r.get('source_url'),r.get('seller'),r.get('product_id'),r.get('currency')) in source_keys]
        measured=sum(w['status']=='MEASURED' for r in measurements for w in r.get('windows',[]))
        linked=[]
        for p in publications:
            linked.append(dict(p,reference_in_title=bool(re.search(r'(?<!\d)'+re.escape(candidate['sku'])+r'(?!\d)',p['title'])),
                relationship='EXPLICIT_REFERENCE_NOT_PROVEN_CAUSE'))
        cases.append({'product_id':cid,'case_kind':'ANNOUNCED_RELEASE_AND_RETAIL_OBSERVATIONS' if release else 'PUBLICATION_AND_RETAIL_OBSERVATIONS' if linked else 'RETAIL_CONTROL_WITHOUT_DISCOVERY_PUBLICATION',
            'announced_release':release,
            'publication_evidence':linked,'candidate_first_observed_at':candidate.get('first_observed_at') if candidate else None,
            'retail_sources':sources,'current_availability_context':product['availability_context'],
            'publication_reaction_measurements':measurements,'measured_publication_reaction_windows':measured,
            'reaction_status':'DESCRIPTIVE_WINDOWS_MEASURED_NOT_CAUSAL' if measured else 'PUBLICATION_REACTION_NOT_MEASURED',
            'missing_data':['VERIFIED_REALIZED_SALES','TRANSACTION_VOLUME','FRANCE_DELIVERED_PRICES','NET_MARGIN']+
                ([] if measured else ['MEASURED_BEFORE_AND_AFTER_PUBLICATION_REACTION']),
            'purchase_gate':product.get('purchase_gate',{'status':'BLOCKED','buy_signal':False,'purchase_authorized':False}),
            'causality_proven':False,'buy_signal':False,'financial_decision':'NOT_ESTABLISHED'})
    return {'schema':'edge.mri.multi_source_cases.v1','generated_at':at,'cases':cases,
        'publication_linked_cases':sum(bool(c['publication_evidence']) for c in cases),
        'measured_publication_reaction_windows':sum(c['measured_publication_reaction_windows'] for c in cases),
        'data_policy':'OBSERVED_PUBLICATIONS_AND_RETAIL_QUOTES_ONLY'}


def render(report):
    lines=['# EDGE — Dossiers de publications et de marché','',
        'Les dates de publication déclarées par les sources, les dates de découverte par EDGE et les heures des relevés sont distinctes. Une mention dans un article ne démontre pas une réaction du marché.','']
    for c in report['cases']:
        if c.get('announced_release'):
            lines+=['Sortie grand public annoncée : '+c['announced_release']['date']+' (date seule, heure inconnue).','']
        lines+=['## '+c['product_id'],'','### Publications archivées','']
        for p in c['publication_evidence']:
            title=p['title'].replace('|','\\|').replace('\n',' ')
            lines.append('- '+p['published_at']+' — ['+title+']('+p['source_url']+') — '+p['signal_context']+' / '+p['source_role'])
        if not c['publication_evidence']:lines.append('Produit témoin : aucune publication de découverte associée.')
        lines+=['','| Vendeur | Premier relevé UTC | Premier prix EUR | Dernier relevé UTC | Dernier prix EUR | Stock déclaré au dernier relevé | Variation depuis le premier relevé |',
            '|---|---|---:|---|---:|---|---:|']
        for s in c['retail_sources']:
            a,b=s['first_observation'],s['latest_observation']
            variation='Non mesuré : premier relevé' if s['displayed_price_change_since_first_capture_pct'] is None else s['displayed_price_change_since_first_capture_pct']+' %'
            lines.append(f"| [{s['seller']}]({s['source_url']}) | {a['observed_at']} | {a['price']} | {b['observed_at']} | {b['price']} | {b['availability']} | {variation} |")
        lines+=['',f"Fenêtres de réaction mesurées autour d’une publication : {c['measured_publication_reaction_windows']}.",
            'Les variations depuis le premier relevé décrivent uniquement la période couverte. Elles ne mesurent pas l’effet de la publication.','',
            'Ventes conclues, volumes, frais livrés et marge nette : non établis. Décision d’achat : non établie.','']
        for measurement in c['publication_reaction_measurements']:
            audit=measurement.get('baseline_audit')
            if not audit:continue
            prior=audit['latest_prior_observation']
            detail=(prior['observed_at']+' ; preuve SHA-256 : '+prior['body_sha256']) if prior else 'aucune capture strictement antérieure'
            lines.append('- Diagnostic avant publication — '+measurement['seller']+' : '+audit['status']+' ; '+detail+'.')
    if not report['cases']:lines.append('Aucun produit avec deux vendeurs actuellement vérifiés dans ce passage.')
    return '\n'.join(lines)+'\n'


def main():
    cli=argparse.ArgumentParser();cli.add_argument('--out',required=True);cli.add_argument('--history',required=True)
    args=cli.parse_args();out,root=Path(args.out),Path(args.history)
    reports=[json.loads(p.read_text()) for p in sorted(root.glob('*/report.json'))]
    market=json.loads((out/'report.json').read_text());reports.append(market)
    discovery=json.loads((out/'discovery.json').read_text())
    context=json.loads((out/'retail_source_context.json').read_text())
    reactions=json.loads((out/'reactions.json').read_text())
    primary=json.loads((out/'primary_verifications.json').read_text())
    result=build(discovery['candidates'],context,reports,reactions,now(),primary)
    (out/'mri_cases.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
    (out/'mri_case_report.md').write_text(render(result))
    market['coverage']['publication_linked_multi_source_cases']=sum(bool(c['publication_evidence']) and len(c['retail_sources'])>=2 for c in result['cases'])
    market['coverage']['announced_release_cases']=sum(bool(c.get('announced_release')) for c in result['cases'])
    (out/'report.json').write_text(json.dumps(market,indent=2,ensure_ascii=False))
    print(json.dumps({'cases':len(result['cases']),'publication_linked_cases':result['publication_linked_cases']}))


if __name__=='__main__':main()
