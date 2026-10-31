"""Follow evidence-verified retail transitions at observation time, never invented event times."""
import argparse
import datetime as dt
import json
from decimal import Decimal
from pathlib import Path

from announcement_history import timestamp
from commercial_history import now
from probability_history import wilson


def scope(row):
    return (row['id'], row['product_id'], row['url'], row['seller'], row.get('currency'))


def follow(events, reports, observed_at):
    at = timestamp(observed_at)
    rows = [r for report in reports for r in report.get('observations', [])
            if r.get('status') == 'OK' and r.get('price_kind') == 'ASKING_PRICE'
            and timestamp(r.get('observed_at')) is not None and timestamp(r['observed_at']) <= at]
    unique_events = {e['id']: e for e in events}
    followed, excluded = [], []
    for event in sorted(unique_events.values(), key=lambda e: e['window_end']):
        if event['kind'] not in ('PRICE_CHANGE', 'AVAILABILITY_CHANGE', 'RESTOCK_OBSERVED'):
            excluded.append({'id': event['id'], 'reason': 'NOT_A_RETAIL_OFFER_TRANSITION'})
            continue
        def matches(row, stamp, sha):
            return (row['id'] == event['observation_id'] and row['product_id'] == event['product_id']
                and row['url'] == event['source_url'] and row['seller'] == event['seller']
                and row['observed_at'] == stamp and row.get('body_sha256') == sha)
        before = next((r for r in rows if matches(r, event['window_start'], event.get('previous_evidence_sha256'))), None)
        detected = next((r for r in rows if matches(r, event['window_end'], event.get('evidence_sha256'))), None)
        field = event['field']
        if (before is None or detected is None or scope(before) != scope(detected)
                or str(before.get(field)) != str(event['before']) or str(detected.get(field)) != str(event['after'])):
            excluded.append({'id': event['id'], 'reason': 'EVENT_EVIDENCE_OR_SCOPE_NOT_VERIFIED'})
            continue
        anchor = timestamp(event['window_end'])
        if anchor > at or timestamp(event['window_start']) >= anchor:
            excluded.append({'id': event['id'], 'reason': 'INVALID_EVENT_TIME_INTERVAL'})
            continue
        family = ('OBSERVED_STOCKOUT' if field == 'availability' and event['before'] == 'IN_STOCK' and event['after'] == 'OUT_OF_STOCK'
                  else 'OBSERVED_RESTOCK' if event['kind'] == 'RESTOCK_OBSERVED'
                  else 'OBSERVED_PRICE_CHANGE' if field == 'price' else 'OBSERVED_AVAILABILITY_CHANGE')
        # Scope remains one product, seller, URL and currency. Failed/unknown captures
        # are never interpreted as a stockout or a negative probability outcome.
        series = { (r['observed_at'], r['body_sha256']): r for r in rows
                  if scope(r) == scope(detected) and timestamp(r['observed_at']) >= anchor }
        series = sorted(series.values(), key=lambda r: timestamp(r['observed_at']))
        latest = series[-1]
        item = {'id': event['id'], 'family': family, 'product_id': event['product_id'],
            'observation_id': event['observation_id'], 'seller': event['seller'], 'source_url': event['source_url'],
            'occurrence_interval_start': event['window_start'], 'occurrence_interval_end': event['window_end'],
            'anchor_kind': 'OBSERVATION_WINDOW_END_NOT_EXACT_EVENT_TIME',
            'field': field, 'before': event['before'], 'after': event['after'],
            'before_price': before['price'], 'detected_price': detected['price'], 'currency': detected['currency'],
            'previous_evidence_sha256': before['body_sha256'], 'detected_evidence_sha256': detected['body_sha256'],
            'latest_observed_at': latest['observed_at'], 'latest_price': latest['price'],
            'latest_availability': latest['availability'], 'latest_evidence_sha256': latest['body_sha256'],
            'elapsed_observed_hours': round((timestamp(latest['observed_at']) - anchor).total_seconds() / 3600, 3),
            'observed_displayed_price_change_pct': str((Decimal(latest['price']) / Decimal(detected['price']) - 1) * 100),
            'successful_captures_since_detection': len(series), 'windows': [],
            'causality_proven': False, 'completed_sale_verified': False, 'buy_signal': False}
        for horizon in (24, 72, 168):
            due = anchor + dt.timedelta(hours=horizon)
            candidates = [r for r in series if due <= timestamp(r['observed_at']) <= due + dt.timedelta(hours=6)]
            window = {'horizon_hours': horizon, 'target_at': due.isoformat(), 'status': 'PENDING_HORIZON'}
            if at >= due:
                window['status'] = 'AWAITING_CAPTURE' if at <= due + dt.timedelta(hours=6) else 'MISSING_WINDOW_OBSERVATION'
                if candidates:
                    after = candidates[0]
                    window.update(status='MEASURED', observed_at=after['observed_at'], price=after['price'],
                        availability=after['availability'], evidence_sha256=after['body_sha256'],
                        observed_displayed_price_change_pct=str((Decimal(after['price']) / Decimal(detected['price']) - 1) * 100))
            item['windows'].append(window)
        followed.append(item)
    return {'schema': 'edge.mri.retail_event_followup.v1', 'observed_at': observed_at,
            'events': followed, 'excluded_events': excluded,
            'scope': 'SAME_SOURCE_POST_DETECTION_DISPLAYED_PRICE_AND_DECLARED_STOCK',
            'causality_proven': False}


def stock_estimates(report, minimum_samples=5):
    estimates = []
    for horizon in (24, 72, 168):
        trials = {event['id']: w for event in report['events'] if event['family'] == 'OBSERVED_STOCKOUT'
                  for w in event['windows'] if w['horizon_hours'] == horizon and w['status'] == 'MEASURED'
                  and w['availability'] in ('IN_STOCK', 'OUT_OF_STOCK')}
        n = len(trials)
        available = sum(w['availability'] == 'IN_STOCK' for w in trials.values())
        enough = n >= minimum_samples
        estimates.append({'horizon_hours': horizon, 'sample_count': n, 'in_stock_count': available,
            'minimum_samples': minimum_samples, 'event_ids': sorted(trials),
            'estimated_probability': available / n if enough else None,
            'binomial_reference_interval_95': wilson(available, n) if enough else None,
            'status': 'ESTIMATED_HISTORICAL_FREQUENCY' if enough else 'INSUFFICIENT_MEASURED_SAMPLE'})
    return {'schema': 'edge.mri.stock_event_estimates.v1', 'observed_at': report['observed_at'],
            'data_kind': 'COMPUTED_ESTIMATE_NOT_OBSERVED_FACT',
            'target': 'IN_STOCK_AT_FIRST_CAPTURE_WITHIN_SIX_HOURS_AFTER_HORIZON_FROM_STOCKOUT_DETECTION',
            'not_a_probability_of': ['restock at any moment during the interval', 'sale', 'profit', 'causal impact'],
            'calibrated_for_future_prediction': False, 'independence_verified': False,
            'estimates': estimates}


def render(report, probabilities):
    lines = ['# EDGE — Suivi des événements commerciaux observés', '', 'Rapport : ' + report['observed_at'], '',
        'Chaque transition est vérifiée contre ses deux captures et leurs empreintes. Son heure exacte reste inconnue entre ces captures. Les variations suivantes sont mesurées après la détection, sur la même source.', '',
        '| Produit | Vendeur | Changement observé | Intervalle de constat UTC | Dernier état observé |', '|---|---|---|---|---|']
    for e in report['events']:
        lines.append(f"| {e['product_id']} | [{e['seller']}]({e['source_url']}) | {e['before']} → {e['after']} | {e['occurrence_interval_start']} → {e['occurrence_interval_end']} | {e['latest_availability']} à {e['latest_observed_at']} |")
        lines += ['', f"Prix affiché lors de la détection : {e['detected_price']} {e['currency']}. Dernier prix affiché : {e['latest_price']} {e['currency']}. Variation observée : {e['observed_displayed_price_change_pct']} %. Captures réussies depuis la détection : {e['successful_captures_since_detection']}.", '']
        for w in e['windows']:
            labels = {'PENDING_HORIZON': 'horizon pas encore atteint', 'AWAITING_CAPTURE': 'capture attendue',
                      'MISSING_WINDOW_OBSERVATION': 'capture manquante dans la fenêtre prévue', 'MEASURED': 'mesuré'}
            lines.append('- ' + str(w['horizon_hours']) + ' h : ' + labels[w['status']] + ' ; cible : ' + w['target_at'])
    lines += ['', '## Estimations de disponibilité après rupture', '',
        'Calcul séparé : fréquence historique de disponibilité au relevé cible après une rupture détectée. Les événements sont dédupliqués. Une capture manquante ne devient pas un résultat négatif.', '',
        '| Horizon | Épisodes mesurés | Disponibles au relevé cible | Estimation |', '|---|---:|---:|---|']
    for r in probabilities['estimates']:
        value = 'Données insuffisantes' if r['estimated_probability'] is None else f"{100*r['estimated_probability']:.1f} %"
        lines.append(f"| {r['horizon_hours']} h | {r['sample_count']} | {r['in_stock_count']} | {value} |")
    lines += ['', 'Les prix affichés et stocks déclarés ne sont ni des ventes conclues ni une mesure de liquidité. L’estimation historique n’est pas calibrée comme prévision future.']
    return '\n'.join(lines) + '\n'


def main():
    cli = argparse.ArgumentParser();cli.add_argument('--out', required=True);cli.add_argument('--history', required=True)
    args = cli.parse_args();out, root = Path(args.out), Path(args.history)
    events, reports = [], []
    for folder in list(root.glob('*')) + [out]:
        for name, target, key in [('events.json', events, 'events'), ('report.json', reports, None)]:
            path = folder / name
            if path.is_file():
                data = json.loads(path.read_text())
                target.extend(data.get(key, [])) if key else target.append(data)
    result = follow(events, reports, now())
    probabilities = stock_estimates(result)
    (out / 'commercial_reactions.json').write_text(json.dumps(result, indent=2, ensure_ascii=False))
    (out / 'market_event_probabilities.json').write_text(json.dumps(probabilities, indent=2, ensure_ascii=False))
    (out / 'commercial_reaction_report.md').write_text(render(result, probabilities))
    market = json.loads((out / 'report.json').read_text())
    market['coverage']['verified_retail_events_followed'] = len(result['events'])
    market['coverage']['measured_retail_event_windows'] = sum(w['status'] == 'MEASURED' for e in result['events'] for w in e['windows'])
    market['coverage']['computed_stock_probability_estimates'] = sum(r['estimated_probability'] is not None for r in probabilities['estimates'])
    (out / 'report.json').write_text(json.dumps(market, indent=2, ensure_ascii=False))
    print(json.dumps({'verified_retail_events': len(result['events']), 'excluded_events': len(result['excluded_events'])}))


if __name__ == '__main__': main()
