"""Explain observed capture gaps and compare source-declared retail states."""
import argparse
import datetime as dt
import json
from pathlib import Path
from decimal import Decimal, InvalidOperation
from announcement_history import timestamp, valid_reaction_quote
from commercial_history import now
from seller_reliability import review_seller, purchase_gate
from collection_policy import EXPECTED_CADENCE_HOURS, TARGET_CAPTURE_TOLERANCE_HOURS


def same_source(row, event):
    return (row.get('id')==event['observation_id'] and row.get('product_id')==event['product_id']
            and row.get('seller')==event['seller'] and row.get('url')==event['source_url']
            and row.get('currency',event['currency'])==event['currency'])


def audit(followup, reports, at):
    current=timestamp(at); incidents=[]
    for event in followup['events']:
        matches=[dict(row, snapshot=r.get('_snapshot',r.get('observed_at'))) for r in reports for row in r['observations']
                 if same_source(row,event) and timestamp(row.get('observed_at')) and timestamp(row['observed_at'])<=current]
        for w in event['windows']:
            if w['status']!='MISSING_WINDOW_OBSERVATION':continue
            start=timestamp(w['target_at']);end=start+dt.timedelta(hours=TARGET_CAPTURE_TOLERANCE_HOURS)
            inside=[r for r in matches if start<=timestamp(r['observed_at'])<=end]
            runs=[r for r in reports if timestamp(r.get('observed_at')) and start<=timestamp(r['observed_at'])<=end]
            if any(r.get('status')=='OK' for r in inside):cause='FOLLOWUP_AND_SOURCE_EVIDENCE_DISAGREE'
            elif inside:cause='SOURCE_REQUESTS_FAILED_IN_TARGET_WINDOW'
            elif runs:cause='SOURCE_NOT_OBSERVED_IN_ARCHIVED_TARGET_RUNS'
            else:cause='NO_ARCHIVED_CAPTURE_RUN_IN_TARGET_WINDOW'
            before=max((r for r in matches if r['status']=='OK' and timestamp(r['observed_at'])<start),
                       key=lambda r:timestamp(r['observed_at']),default=None)
            after=min((r for r in matches if r['status']=='OK' and timestamp(r['observed_at'])>end),
                      key=lambda r:timestamp(r['observed_at']),default=None)
            def evidence(row):
                return {k:row.get(k) for k in ('snapshot','id','observed_at','status','availability','price','currency','body_sha256','error_type','error')} if row else None
            incidents.append({'event_id':event['id'],'product_id':event['product_id'],'seller':event['seller'],
                'source_url':event['source_url'],'horizon_hours':w['horizon_hours'],'window_start':w['target_at'],
                'window_end':end.isoformat(),'diagnosis':cause,'archived_runs_in_window':len(runs),
                'source_attempts_in_window':[evidence(r) for r in inside],
                'last_success_before':evidence(before),'first_success_after':evidence(after),
                'successful_capture_gap_hours':round((timestamp(after['observed_at'])-timestamp(before['observed_at'])).total_seconds()/3600,3) if before and after else None,
                'scheduler_root_cause_proven':False,'missing_outcome_filled':False})
    report_times=sorted({timestamp(r['observed_at']) for r in reports if timestamp(r.get('observed_at')) and timestamp(r['observed_at'])<=current})
    gaps=[{'previous_run_observed_at':a.isoformat(),'next_run_observed_at':b.isoformat(),
           'gap_hours':round((b-a).total_seconds()/3600,3)} for a,b in zip(report_times,report_times[1:])
          if b-a>dt.timedelta(hours=TARGET_CAPTURE_TOLERANCE_HOURS)]
    return {'schema':'edge.mri.collection_coverage.v1','generated_at':at,
        'status':'INCIDENTS_PRESENT' if incidents else 'NO_MISSING_TARGET_WINDOWS_OBSERVED',
        'expected_cadence_hours':EXPECTED_CADENCE_HOURS,'capture_window_tolerance_hours':TARGET_CAPTURE_TOLERANCE_HOURS,
        'observed_inter_run_gaps_over_six_hours':gaps,'missed_targets':incidents,
        'latest_archived_or_current_run_at':report_times[-1].isoformat() if report_times else None,
        'scheduler_root_cause_proven':False,'alert_delivery':'REPORT_ONLY_NO_EXTERNAL_MESSAGES'}


def source_context(market, at, seller_reviews=None):
    current=timestamp(at); products={}
    for row in market['observations']:
        if row.get('price_kind')!='ASKING_PRICE':continue
        group=products.setdefault(row['product_id'],{})
        # One current observation per retailer; multiple pages are not independent sellers.
        old=group.get(row['seller'])
        if old is None or (timestamp(row.get('observed_at')) or dt.datetime.min.replace(tzinfo=dt.timezone.utc))>(timestamp(old.get('observed_at')) or dt.datetime.min.replace(tzinfo=dt.timezone.utc)):
            group[row['seller']]=row
    result=[]
    for product, sellers in sorted(products.items()):
        sources=[]
        for row in sellers.values():
            stamp=timestamp(row.get('observed_at'))
            try:
                price=Decimal(str(row.get('price')))
                valid_price=price.is_finite() and price>0
            except InvalidOperation:
                valid_price=False
            usable=(valid_price and row['status']=='OK' and row.get('currency')=='EUR' and stamp is not None
                    and 0<=(current-stamp).total_seconds()<=86400)
            sources.append({'seller':row['seller'],'source_url':row['url'],'observed_at':row.get('observed_at'),
                'status':row['status'],'usable_current_quote':usable,
                'availability':row.get('availability','UNKNOWN') if usable else 'UNKNOWN',
                'displayed_price_eur':row.get('price') if usable else None,'body_sha256':row.get('body_sha256'),
                'shipping_eur':row.get('shipping_eur'),'error':row.get('error'),
                'shipping_to_france_verified':row.get('evidence',{}).get('shipping_to_france_verified'),
                'seller_reliability':review_seller(row['seller'],row['url'],seller_reviews,at),
                'retailer_announced_available_date':row.get('evidence',{}).get('retailer_announced_available_date')})
        valid=[s for s in sources if s['usable_current_quote']]
        available=[s for s in valid if s['availability']=='IN_STOCK']
        stockouts=[s for s in valid if s['availability']=='OUT_OF_STOCK']
        upcoming=[s for s in valid if s['availability']=='COMING_SOON']
        state=('MIXED_AVAILABILITY_ON_OBSERVED_SOURCES' if available and stockouts else
               'OUT_OF_STOCK_ON_MULTIPLE_OBSERVED_SOURCES' if len(stockouts)>=2 else
               'SINGLE_SOURCE_STOCKOUT' if stockouts else
               'IN_STOCK_ON_OBSERVED_SOURCES' if available else
               'COMING_SOON_ON_OBSERVED_SOURCES' if upcoming else 'AVAILABILITY_NOT_ESTABLISHED')
        result.append({'product_id':product,'sources':sources,'verified_current_seller_count':len(valid),
            'in_stock_seller_count':len(available),'out_of_stock_seller_count':len(stockouts),
            'availability_context':state,
            'lowest_observed_in_stock_asking_price_eur':str(min(Decimal(s['displayed_price_eur']) for s in available)) if available else None,
            'market_wide_shortage_proven':False,'completed_sales_verified':False,'buy_signal':False,
            'purchase_gate':purchase_gate(sources,at),
            'lowest_reviewed_seller_in_stock_price_eur':str(min(Decimal(s['displayed_price_eur']) for s in available if s['seller_reliability']['eligible_for_economic_use'])) if any(s['seller_reliability']['eligible_for_economic_use'] for s in available) else None})
    return {'schema':'edge.mri.retail_source_context.v1','generated_at':at,'products':result,
            'scope':'CURRENT_RUN_QUOTES_WITHIN_24_HOURS_NOT_EXHAUSTIVE_MARKET','net_margin_computed':False}


def preparation(context, reports, at):
    """Describe existing evidence for a future event, never a forecast or a signal."""
    current=timestamp(at); products=[]
    for product in context['products']:
        sources=[]
        for source in product['sources']:
            by_time={}
            for report in reports:
                for r in report['observations']:
                    if (r.get('product_id')!=product['product_id'] or r.get('seller')!=source['seller']
                        or r.get('url')!=source['source_url'] or r.get('currency')!='EUR'
                        or r.get('status')!='OK' or r.get('price_kind')!='ASKING_PRICE'
                        or not valid_reaction_quote(r) or timestamp(r['observed_at'])>current):continue
                    by_time.setdefault(timestamp(r['observed_at']),[]).append(r)
            rows=[];conflicts=0
            for stamp, copies in sorted(by_time.items()):
                if len({(Decimal(r['price']),r.get('availability')) for r in copies})>1:
                    conflicts+=1;continue
                rows.append(min(copies,key=lambda r:(r['body_sha256'],r['id'])))
            recent=[r for r in rows if current-dt.timedelta(hours=24)<=timestamp(r['observed_at'])]
            latest=rows[-1] if rows else None
            gaps=[round((timestamp(b['observed_at'])-timestamp(a['observed_at'])).total_seconds()/3600,3)
                  for a,b in zip(recent,recent[1:])]
            status=('NO_VALID_CAPTURE' if not latest else 'STALE_HISTORY' if not recent else
                    'COLLECTION_INTERRUPTED' if not source['usable_current_quote'] else
                    'SINGLE_RECENT_CAPTURE' if len(recent)==1 else
                    'GAPPED_RECENT_SERIES' if any(g>TARGET_CAPTURE_TOLERANCE_HOURS for g in gaps) else 'RECENT_SERIES')
            evidence={k:latest.get(k) for k in ('id','observed_at','price','currency','availability','body_sha256')} if latest else None
            sources.append({'seller':source['seller'],'source_url':source['source_url'],'status':status,
                'successful_distinct_capture_count':len(rows),'recent_distinct_capture_count':len(recent),
                'conflicting_timestamps_excluded':conflicts,'latest_valid_evidence':evidence,
                'potential_baseline_expires_at':(timestamp(latest['observed_at'])+dt.timedelta(hours=24)).isoformat() if latest else None,
                'recent_max_gap_hours':max(gaps) if gaps else None,
                'has_recent_potential_baseline':bool(recent),'current_source_status':source['status']})
        sellers={s['seller'] for s in sources if s['has_recent_potential_baseline']}
        products.append({'product_id':product['product_id'],'recent_baseline_seller_count':len(sellers),'sources':sources})
    return {'assessed_at':at,'scope':'POTENTIAL_BASELINES_FOR_FUTURE_EVENTS_NOT_RETROACTIVE_REACTIONS',
            'maximum_baseline_age_hours':24,'products':products,
            'products_with_recent_baseline':sum(p['recent_baseline_seller_count']>0 for p in products),
            'products_with_multiple_baseline_sellers':sum(p['recent_baseline_seller_count']>=2 for p in products),
            'buy_signal':False,'predictive_advantage_established':False}


def render(coverage, context):
    labels={'NO_ARCHIVED_CAPTURE_RUN_IN_TARGET_WINDOW':'Aucun passage archivé dans la fenêtre',
        'SOURCE_REQUESTS_FAILED_IN_TARGET_WINDOW':'Échecs de source dans la fenêtre',
        'SOURCE_NOT_OBSERVED_IN_ARCHIVED_TARGET_RUNS':'Source absente des passages archivés',
        'FOLLOWUP_AND_SOURCE_EVIDENCE_DISAGREE':'Incohérence à examiner entre suivi et captures'}
    lines=['# EDGE — Qualité de collecte et disponibilité par vendeur','',
        'Cadence visée : toutes les trois heures. Les retards du planificateur restent possibles. Les incidents ci-dessous constatent les preuves archivées ; la cause technique d’un passage absent reste à établir.','',
        '| Produit | Horizon manqué | Constat | Intervalle entre relevés réussis |','|---|---:|---|---|']
    for i in coverage['missed_targets']:
        lines.append(f"| {i['product_id']} | {i['horizon_hours']} h | {labels[i['diagnosis']]} | {i['successful_capture_gap_hours']} h |")
    lines+=['','## Sources commerciales du passage','',
        '| Produit | Vendeur | Prix affiché EUR | Stock déclaré | Heure du relevé UTC |','|---|---|---:|---|---|']
    stock={'IN_STOCK':'En stock','OUT_OF_STOCK':'Rupture','UNKNOWN':'Inconnu','PREORDER':'Précommande','BACKORDER':'Sur commande','DISCONTINUED':'Arrêté','COMING_SOON':'À venir'}
    for p in context['products']:
        for s in p['sources']:
            price=s['displayed_price_eur'] or 'Non établi'
            lines.append(f"| {p['product_id']} | [{s['seller']}]({s['source_url']}) | {price} | {stock.get(s['availability'],s['availability'])} | {s['observed_at']} |")
    lines+=['','## Préparation aux prochains événements','',
        'État à la date de capture. Un relevé récent constitue seulement un point de départ potentiel pour un événement futur. Sa validité devra être recalculée à la date de cet événement.','',
        '| Produit | Vendeur | État du suivi | Captures distinctes sur 24 h | Dernière preuve UTC | Expiration du point de départ |',
        '|---|---|---|---:|---|---|']
    for p in coverage.get('event_preparation',{}).get('products',[]):
        for s in p['sources']:
            latest=s['latest_valid_evidence']
            lines.append(f"| {p['product_id']} | {s['seller']} | {s['status']} | {s['recent_distinct_capture_count']} | {latest['observed_at'] if latest else 'Absente'} | {s['potential_baseline_expires_at'] or 'Non établie'} |")
    lines+=['','Une rupture chez un vendeur ne prouve pas une pénurie du marché. Les offres moins chères en rupture restent distinctes des offres disponibles. Frais de livraison, ventes conclues et marge nette ne sont pas établis par cette comparaison. Aucune donnée manquante n’est interpolée.']
    return '\n'.join(lines)+'\n'


def main():
    cli=argparse.ArgumentParser();cli.add_argument('--out',required=True);cli.add_argument('--history',required=True)
    args=cli.parse_args();out,root=Path(args.out),Path(args.history)
    reports=[]
    for p in sorted(root.glob('*/report.json')):
        r=json.loads(p.read_text());r['_snapshot']=p.parent.name;reports.append(r)
    market=json.loads((out/'report.json').read_text());reports.append(dict(market,_snapshot='CURRENT_RUN'))
    followup=json.loads((out/'commercial_reactions.json').read_text());at=now()
    seller_reviews=json.loads(Path('seller_reviews.json').read_text())
    coverage=audit(followup,reports,at);context=source_context(market,at,seller_reviews)
    coverage['event_preparation']=preparation(context,reports,at)
    previous_keys={(i['event_id'],i['horizon_hours'],i['window_start'],i['diagnosis'])
        for p in root.glob('*/collection_coverage.json') for i in json.loads(p.read_text()).get('missed_targets',[])}
    coverage['new_incident_count']=sum((i['event_id'],i['horizon_hours'],i['window_start'],i['diagnosis']) not in previous_keys for i in coverage['missed_targets'])
    for i in coverage['missed_targets']:
        if (i['event_id'],i['horizon_hours'],i['window_start'],i['diagnosis']) not in previous_keys:
            print('::warning::Missing target capture: '+i['product_id']+' / '+str(i['horizon_hours'])+'h / '+i['diagnosis'])
    (out/'collection_coverage.json').write_text(json.dumps(coverage,indent=2,ensure_ascii=False))
    (out/'retail_source_context.json').write_text(json.dumps(context,indent=2,ensure_ascii=False))
    (out/'coverage_report.md').write_text(render(coverage,context))
    market['coverage']['missing_target_window_incidents']=len(coverage['missed_targets'])
    market['coverage']['products_with_multiple_current_retailers']=sum(p['verified_current_seller_count']>=2 for p in context['products'])
    market['coverage']['seller_review_eligible_in_stock_offers']=sum(p['purchase_gate']['seller_eligible_offer_count'] for p in context['products'])
    market['coverage']['unverified_seller_current_prices']=sum(s['usable_current_quote'] and not s['seller_reliability']['eligible_for_economic_use'] for p in context['products'] for s in p['sources'])
    (out/'report.json').write_text(json.dumps(market,indent=2,ensure_ascii=False))
    print(json.dumps({'missing_target_incidents':len(coverage['missed_targets']),
        'multiple_current_retailers':market['coverage']['products_with_multiple_current_retailers']}))


if __name__=='__main__':main()
