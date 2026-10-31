"""Chronological retrieval of observed retail episodes; similarity is not probability."""
import argparse
import datetime as dt
import json
from pathlib import Path

from announcement_history import timestamp
from commercial_history import now
from commercial_reaction_history import follow
from probability_history import wilson

METHOD = 'RETAIL_EVENT_ANALOGUES_V1'
MIN_SCORE = 0.75  # Fixed research rule, not fitted or validated predictive threshold.


def configuration(event, reports):
    """Freeze features at detection. Never use the event's later follow-up fields."""
    anchor = timestamp(event['occurrence_interval_end'])
    rows = [r for report in reports for r in report.get('observations', [])
            if r.get('status') == 'OK' and r.get('price_kind') == 'ASKING_PRICE'
            and r.get('id') == event['observation_id'] and r.get('product_id') == event['product_id']
            and r.get('url') == event['source_url'] and r.get('seller') == event['seller']
            and r.get('currency') == event['currency'] and timestamp(r.get('observed_at'))
            and anchor - dt.timedelta(hours=72) <= timestamp(r['observed_at']) <= anchor]
    rows = sorted({(r['observed_at'], r['body_sha256']): r for r in rows}.values(),
                  key=lambda r: timestamp(r['observed_at']))
    # Require a genuine earlier observation, at least six hours before detection.
    earlier = [r for r in rows if timestamp(r['observed_at']) <= anchor - dt.timedelta(hours=6)]
    change = None
    if earlier:
        change = (float(event['detected_price']) / float(earlier[0]['price']) - 1) * 100
    return {'event_id': event['id'], 'product_id': event['product_id'], 'as_of': anchor.isoformat(),
            'family': event['family'], 'currency': event['currency'], 'seller': event['seller'],
            'price': float(event['detected_price']), 'month': anchor.month,
            'prior_price_change_pct': change,
            'prior_price_baseline_at': earlier[0]['observed_at'] if earlier else None,
            'evidence': [{'observed_at': r['observed_at'], 'body_sha256': r['body_sha256'], 'url': r['url']} for r in rows],
            'unavailable_features': ['licence', 'distribution', 'production_quantity', 'transaction_volume', 'net_margin']}


def similarity(query, candidate):
    # Equal weights, all four features required. Product IDs and outcomes are never features.
    if query['prior_price_change_pct'] is None or candidate['prior_price_change_pct'] is None:
        return None
    month_distance = min(abs(query['month'] - candidate['month']), 12 - abs(query['month'] - candidate['month']))
    components = {'price_ratio': min(query['price'], candidate['price']) / max(query['price'], candidate['price']),
                  'season': 1 - month_distance / 6,
                  'same_seller': float(query['seller'] == candidate['seller']),
                  'prior_price_change': 1 / (1 + abs(query['prior_price_change_pct'] - candidate['prior_price_change_pct']) / 10)}
    return {'score': round(sum(components.values()) / len(components), 6), 'components': components,
            'data_kind': 'UNCALIBRATED_HEURISTIC_SIMILARITY_NOT_PROBABILITY'}


def retrieve(followup, reports):
    events = {e['id']: e for e in followup['events']}
    configs = {key: configuration(e, reports) for key, e in events.items()}
    queries = []
    for key, query in configs.items():
        anchor = timestamp(query['as_of'])
        horizons = []
        for horizon in (24, 72, 168):
            eligible, exclusions = [], []
            for other, candidate in configs.items():
                reason = None
                if other == key: reason = 'SELF'
                elif candidate['product_id'] == query['product_id']: reason = 'SAME_PRODUCT_DEPENDENCE'
                elif candidate['family'] != query['family'] or candidate['currency'] != query['currency']:
                    reason = 'DIFFERENT_EVENT_FAMILY_OR_CURRENCY'
                elif timestamp(candidate['as_of']) >= anchor: reason = 'NOT_PRIOR_TO_QUERY'
                window = next((w for w in events[other]['windows'] if w['horizon_hours'] == horizon), None)
                if reason is None and (not window or window['status'] != 'MEASURED'
                        or timestamp(window.get('observed_at')) is None or timestamp(window['observed_at']) > anchor):
                    reason = 'OUTCOME_NOT_KNOWN_AT_QUERY_TIME'
                comparison = similarity(query, candidate) if reason is None else None
                if reason is None and comparison is None: reason = 'INCOMPLETE_PRIOR_FEATURES'
                if reason is None and comparison['score'] < MIN_SCORE: reason = 'BELOW_RESEARCH_SIMILARITY_THRESHOLD'
                if reason:
                    exclusions.append({'event_id': other, 'reason': reason})
                else:
                    eligible.append({'event_id': other, 'product_id': candidate['product_id'],
                        'as_of': candidate['as_of'], 'similarity': comparison, 'measured_outcome': window,
                        'source_url': events[other]['source_url'], 'configuration': candidate})
            eligible.sort(key=lambda r: (-r['similarity']['score'], r['event_id']))
            # One precedent per product, even if multiple sellers/days would match.
            selected, products = [], set()
            for candidate in eligible:
                if candidate['product_id'] in products:
                    exclusions.append({'event_id': candidate['event_id'], 'reason': 'PRODUCT_ALREADY_REPRESENTED'})
                elif len(selected) < 20:
                    selected.append(candidate); products.add(candidate['product_id'])
                else:
                    exclusions.append({'event_id': candidate['event_id'], 'reason': 'RETRIEVAL_LIMIT'})
            trials = [r for r in selected if r['measured_outcome'].get('availability') in ('IN_STOCK', 'OUT_OF_STOCK')]
            n = len(trials); hits = sum(r['measured_outcome']['availability'] == 'IN_STOCK' for r in trials)
            enough = n >= 5
            horizons.append({'horizon_hours': horizon, 'analogues': selected, 'exclusions': exclusions,
                'sample_count': n, 'in_stock_count': hits, 'minimum_samples': 5,
                'estimated_in_stock_frequency': hits / n if enough else None,
                'binomial_reference_interval_95': wilson(hits, n) if enough else None,
                'status': 'COMPUTED_HISTORICAL_FREQUENCY' if enough else 'INSUFFICIENT_COMPARABLE_HISTORY'})
        queries.append({'event_id': key, 'product_id': query['product_id'], 'configuration': query,
                        'horizons': horizons, 'buy_signal': False})
    return {'schema': 'edge.mri.retail_analogues.v1', 'generated_at': followup['observed_at'], 'method': METHOD,
        'similarity_threshold': MIN_SCORE, 'maximum_analogues': 20,
        'policy': 'FEATURES_AND_PRECEDENT_OUTCOMES_KNOWN_AT_QUERY_DETECTION_TIME',
        'feature_weights': 'EQUAL; PRICE_RATIO, CIRCULAR_MONTH, SAME_SELLER, PRIOR_PRICE_CHANGE',
        'threshold_and_weights_validated': False, 'independence_verified': False,
        'calibrated_for_future_prediction': False, 'out_of_sample_performance': None,
        'probability_target': 'SOURCE_DECLARED_IN_STOCK_AT_TARGET_CAPTURE',
        'not_a_probability_of': ['profit', 'sale', 'optimal_entry_or_exit'],
        'verified_episode_count': len(events), 'queries': queries}


def render(report):
    lines = ['# EDGE — Comparaison de configurations historiques', '',
        'Méthode : ' + report['method'] + '. Chaque recherche est figée à la détection de son événement.', '',
        '| Produit | Horizon | Précédents comparables mesurés | Fréquence calculée |', '|---|---:|---:|---|']
    for query in report['queries']:
        for row in query['horizons']:
            value = 'Données insuffisantes' if row['estimated_in_stock_frequency'] is None else str(round(row['estimated_in_stock_frequency'] * 100, 1)) + ' %'
            lines.append(f"| {query['product_id']} | {row['horizon_hours']} h | {row['sample_count']} | {value} |")
    lines += ['', 'Le score de ressemblance est une règle de recherche non calibrée, pas une probabilité. Les poids, le seuil de 0,75 et le minimum de cinq produits ne constituent pas une validation prédictive.', '',
        'Les caractéristiques utilisent seulement le prix, le mois, le vendeur et la variation de prix connue avant la détection. Licence, distribution, quantités produites, ventes et marge ne sont pas renseignées.', '',
        'Les événements futurs, les résultats encore inconnus à la date du signal et les répétitions du même produit sont exclus. Les motifs et empreintes sont conservés dans analogue_matches.json.', '',
        'Aucune performance hors échantillon ni fenêtre optimale d’achat ou de revente n’est établie.']
    return '\n'.join(lines) + '\n'


def main():
    cli = argparse.ArgumentParser(); cli.add_argument('--out', required=True); cli.add_argument('--history', required=True)
    args = cli.parse_args(); out, root = Path(args.out), Path(args.history)
    reports, events = [], []
    for folder in list(root.glob('*')) + [out]:
        for name, target, key in [('report.json', reports, None), ('events.json', events, 'events')]:
            path = folder / name
            if path.is_file():
                data = json.loads(path.read_text())
                target.extend(data.get(key, [])) if key else target.append(data)
    result = retrieve(follow(events, reports, now()), reports)
    (out / 'analogue_matches.json').write_text(json.dumps(result, indent=2, ensure_ascii=False))
    (out / 'analogue_report.md').write_text(render(result))
    market = json.loads((out / 'report.json').read_text())
    market['coverage']['analogue_queries'] = len(result['queries'])
    market['coverage']['analogue_queries_with_sufficient_history'] = sum(any(h['estimated_in_stock_frequency'] is not None for h in q['horizons']) for q in result['queries'])
    (out / 'report.json').write_text(json.dumps(market, indent=2, ensure_ascii=False))
    print(json.dumps({'verified_episodes': result['verified_episode_count'], 'queries': len(result['queries'])}))


if __name__ == '__main__': main()
