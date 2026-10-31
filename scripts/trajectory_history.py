"""Retrospective, ordered monthly analogue research; never a live investment signal."""
import argparse
import gzip
import hashlib
import json
import math
import re
from pathlib import Path
from statistics import mean, median

from commercial_history import now
from monthly_history import IMPORT_ID, SHA256, month_index

HORIZONS = (1, 3, 6, 12)
K = 20
MIN_SAMPLE = 10
MAX_LOG_DISTANCE = 0.10
QUERY_MONTHS = tuple(f'{year}-{month:02d}' for year in (2021, 2022, 2023)
                     for month in (3, 6, 9, 12) if (year, month) <= (2023, 6))
QUERIES_PER_MONTH = 20


def month_name(index):
    year, month = divmod(index - 1, 12)
    return f'{year:04d}-{month+1:02d}'


def product_group(series):
    # Conservative shared reference hint; not an official set/variant identity claim.
    path = series['source_url'].rsplit('/', 1)[-1].rsplit('-h', 1)[0]
    match = re.search(r'(?<!\d)(\d{4,7})(?!\d)', path)
    return 'URL_REFERENCE_HINT:' + match.group(1) if match else 'SERIES:' + series['id']


def build_episodes(series):
    episodes = []
    dataset_end = max((month_index(p['month']) for s in series for p in s['points']), default=0)
    seen = set()
    for s in sorted(series, key=lambda s: s['id']):
        if s['id'] in seen: raise ValueError('Duplicate normalized series ID')
        seen.add(s['id'])
        points = {}
        for p in s['points']:
            index = month_index(p['month'])
            if index in points: raise ValueError('Duplicate normalized series month')
            price = float(p['price_pln']) if p['price_pln'] is not None else None
            if price is not None and (not math.isfinite(price) or price <= 0):
                raise ValueError('Nonpositive/nonfinite normalized price')
            points[index] = dict(p, price=price)
        for anchor in sorted(points):
            prior = [points.get(m) for m in range(anchor-3, anchor+1)]
            if any(p is None or p['price'] is None for p in prior): continue
            returns = [math.log(prior[i]['price'] / prior[i-1]['price']) for i in range(1, 4)]
            change = (prior[-1]['price'] / prior[0]['price'] - 1) * 100
            config = {'id': s['id'] + ':' + month_name(anchor), 'series_id': s['id'],
                'product_group_hint': product_group(s), 'source_url': s['source_url'],
                'anchor_month': month_name(anchor), 'anchor_index': anchor,
                'price_pln': prior[-1]['price'], 'monthly_log_changes': returns,
                'three_month_change_pct': change,
                'price_phase': 'RISING' if change > 1 else 'FALLING' if change < -1 else 'STABLE_WITHIN_ONE_PERCENT',
                'evidence': [{'month': p['month'], 'source_row': p['source_row'], 'price_pln': p['price_pln']} for p in prior]}
            outcomes, outcome_gaps = {}, {}
            for horizon in HORIZONS:
                future = [points.get(m) for m in range(anchor+1, anchor+horizon+1)]
                if any(p is None or p['price'] is None for p in future):
                    outcome_gaps[horizon] = 'AFTER_DATASET_END' if anchor+horizon > dataset_end else 'INCOMPLETE_SERIES_MONTHS'
                    continue
                last = future[-1]
                outcomes[horizon] = {'target_month': last['month'], 'target_index': anchor+horizon,
                    'price_pln': last['price_pln'], 'change_pct': (last['price'] / prior[-1]['price'] - 1) * 100,
                    'source_row': last['source_row'], 'complete_intermediate_months': True}
            episodes.append({'configuration': config, 'outcomes': outcomes, 'outcome_gaps': outcome_gaps})
    return episodes


def quantile(values, fraction):
    values = sorted(values)
    position = (len(values)-1)*fraction
    lo = int(position); hi = min(lo+1, len(values)-1)
    return values[lo] + (values[hi]-values[lo])*(position-lo)


def distance(query, candidate):
    season_distance = abs(query['anchor_index'] % 12 - candidate['anchor_index'] % 12)
    season_distance = min(season_distance, 12-season_distance)
    if season_distance > 1: return None
    ratio = min(query['price_pln'], candidate['price_pln']) / max(query['price_pln'], candidate['price_pln'])
    if ratio < 0.5: return None
    score = mean(abs(a-b) for a,b in zip(query['monthly_log_changes'], candidate['monthly_log_changes']))
    return score if score <= MAX_LOG_DISTANCE else None


def predict(query, episodes):
    """Query has no future outcome. Candidate outcomes must predate query month."""
    per_horizon = {h: [] for h in HORIZONS}
    baselines = {h: {} for h in HORIZONS}
    for episode in episodes:
        candidate = episode['configuration']
        if candidate['product_group_hint'] == query['product_group_hint']: continue
        if candidate['anchor_index'] >= query['anchor_index']: continue
        d = distance(query, candidate)
        for h, outcome in episode['outcomes'].items():
            # One full calendar-month embargo: target must be before query month.
            if outcome['target_index'] >= query['anchor_index']: continue
            old = baselines[h].get(candidate['product_group_hint'])
            if old is None or candidate['anchor_index'] > old['configuration']['anchor_index']:
                baselines[h][candidate['product_group_hint']] = episode
            if d is not None:
                per_horizon[h].append((d, candidate['id'], episode))
    predictions = []
    for h in HORIZONS:
        matches, groups = [], set()
        for d, _, episode in sorted(per_horizon[h], key=lambda x: (x[0], x[1])):
            config = episode['configuration']; group = config['product_group_hint']
            if group in groups: continue
            groups.add(group)
            matches.append({'distance_mean_absolute_log_change': d, 'configuration': config,
                            'outcome': episode['outcomes'][h]})
            if len(matches) == K: break
        values = [r['outcome']['change_pct'] for r in matches]
        enough = len(values) >= MIN_SAMPLE
        baseline = [e['outcomes'][h]['change_pct'] for e in baselines[h].values()]
        predictions.append({'horizon_months': h, 'status': 'COMPUTED_RETROSPECTIVE_ESTIMATE' if enough else 'INSUFFICIENT_ANALOGUES',
            'sample_count': len(values), 'matches': matches,
            'estimated_positive_change_frequency': mean(v > 0 for v in values) if enough else None,
            'estimated_median_change_pct': median(values) if enough else None,
            'historical_outcome_p10_pct': quantile(values, .1) if enough else None,
            'historical_outcome_p90_pct': quantile(values, .9) if enough else None,
            'baseline_prior_group_count': len(baseline),
            'baseline_positive_change_frequency': mean(v > 0 for v in baseline) if baseline else None,
            'baseline_median_change_pct': median(baseline) if baseline else None,
            'numeric_kind': 'COMPUTED_ESTIMATE_NOT_OBSERVED_FACT', 'buy_signal': False})
    return predictions


def choose_queries(episodes):
    """Select by known features and fixed hash, before inspecting future completeness."""
    selected = []
    for month in QUERY_MONTHS:
        candidates = [e for e in episodes if e['configuration']['anchor_month'] == month]
        candidates.sort(key=lambda e: hashlib.sha256(('EDGE_TRAJECTORY_V1:' + e['configuration']['id']).encode()).hexdigest())
        groups = set()
        for e in candidates:
            group = e['configuration']['product_group_hint']
            if group in groups: continue
            selected.append(e); groups.add(group)
            if len(groups) == QUERIES_PER_MONTH: break
    return selected


def metrics(evaluations):
    result = []
    for h in HORIZONS:
        forecasts = [p for q in evaluations for p in q['predictions'] if p['horizon_months'] == h]
        rows = [p for p in forecasts if p['status'] == 'COMPUTED_RETROSPECTIVE_ESTIMATE' and p.get('actual_outcome')]
        tp = fp = tn = fn = 0
        for p in rows:
            positive = p['estimated_positive_change_frequency'] >= .5
            actual = p['actual_outcome']['change_pct'] > 0
            tp += positive and actual; fp += positive and not actual
            tn += not positive and not actual; fn += not positive and actual
        n = len(rows)
        def average(fn): return mean(fn(p) for p in rows) if rows else None
        brier = average(lambda p: (p['estimated_positive_change_frequency'] - (p['actual_outcome']['change_pct'] > 0))**2)
        base_brier = average(lambda p: (p['baseline_positive_change_frequency'] - (p['actual_outcome']['change_pct'] > 0))**2)
        mae = average(lambda p: abs(p['estimated_median_change_pct'] - p['actual_outcome']['change_pct']))
        no_change_mae = average(lambda p: abs(p['actual_outcome']['change_pct']))
        prior_mae = average(lambda p: abs(p['baseline_median_change_pct'] - p['actual_outcome']['change_pct']))
        result.append({'horizon_months': h, 'selected_queries': len(forecasts),
            'sufficient_analogue_queries': sum(p['status'] == 'COMPUTED_RETROSPECTIVE_ESTIMATE' for p in forecasts),
            'unmeasured_query_outcomes': sum(p.get('actual_outcome') is None for p in forecasts),
            'outcomes_after_dataset_end': sum(p.get('actual_outcome_status') == 'AFTER_DATASET_END' for p in forecasts),
            'outcomes_with_incomplete_series': sum(p.get('actual_outcome_status') == 'INCOMPLETE_SERIES_MONTHS' for p in forecasts),
            'paired_evaluations': n, 'true_positive': tp, 'false_positive': fp, 'true_negative': tn, 'false_negative': fn,
            'direction_accuracy': (tp+tn)/n if n else None,
            'baseline_direction_accuracy': average(lambda p: (p['baseline_positive_change_frequency'] >= .5) == (p['actual_outcome']['change_pct'] > 0)),
            'brier_score': brier, 'baseline_prior_frequency_brier': base_brier,
            'brier_improvement': base_brier-brier if n else None,
            'mean_absolute_error_pct_points': mae, 'no_change_baseline_mae_pct_points': no_change_mae,
            'prior_median_baseline_mae_pct_points': prior_mae,
            'paired_scope': 'SAME_QUERIES_WITH_SUFFICIENT_ANALOGUES_AND_MEASURED_OUTCOME',
            'predictive_advantage_established': False})
    return result


def evaluate(episodes):
    queries = choose_queries(episodes)
    evaluations = []
    for episode in queries:
        query = episode['configuration']
        predictions = predict(query, episodes)
        # Held-out target is joined only after retrieval and estimation.
        for p in predictions:
            p['actual_outcome'] = episode['outcomes'].get(p['horizon_months'])
            p['actual_outcome_status'] = 'MEASURED' if p['actual_outcome'] else episode['outcome_gaps'][p['horizon_months']]
        evaluations.append({'configuration': query, 'predictions': predictions})
    return evaluations


def render(report):
    lines = ['# EDGE — Comparaison des trajectoires mensuelles', '',
        'Analyse rétrospective ordonnée sur des maxima mensuels polonais en PLN. Aucune estimation de marge nette ni de prix de vente encaissé.', '',
        f"Configurations de quatre mois : {report['episode_count']}. Requêtes de test déterministes : {report['evaluation_query_count']}.", '',
        'Les précédents appartiennent à d’autres références présumées et leur résultat doit se terminer avant le mois du signal testé. Les mois manquants interrompent la trajectoire. Les dates de publication historiques et révisions ne sont pas vérifiées.', '',
        '| Horizon | Tests appariés | MAE analogues (points de %) | MAE aucun changement | MAE médiane passée | Brier analogues | Brier fréquence passée | Faux signaux de hausse |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    def value(x): return 'Non calculé' if x is None else f'{x:.4f}'
    for r in report['evaluation_metrics']:
        lines.append(f"| {r['horizon_months']} mois | {r['paired_evaluations']} | {value(r['mean_absolute_error_pct_points'])} | {value(r['no_change_baseline_mae_pct_points'])} | {value(r['prior_median_baseline_mae_pct_points'])} | {value(r['brier_score'])} | {value(r['baseline_prior_frequency_brier'])} | {r['false_positive']} |")
    lines += ['', 'MAE et score de Brier : une valeur plus basse est préférable. Les références et le modèle sont évalués sur les mêmes requêtes mesurables. Les faux signaux sont des estimations de hausse dont le maximum mensuel cible ne monte pas ; ils ne représentent pas des opérations financières.', '',
        '## Exemple fixé avant mesure : série source 10312, juin 2023', '',
        'Cette date est la fin de l’historique. Ses résultats futurs restent inconnus dans le fichier ; les estimations ci-dessous ne constituent pas une prévision actuelle.', '',
        '| Horizon | Précédents retenus | Fréquence historique de hausse | Médiane des évolutions | Dispersion p10–p90 |', '|---|---:|---:|---:|---|']
    for p in report['fixed_example'].get('predictions', []):
        frequency = p['estimated_positive_change_frequency']
        lines.append(f"| {p['horizon_months']} mois | {p['sample_count']} | {value(None if frequency is None else frequency*100)} % | {value(p['estimated_median_change_pct'])} % | {value(p['historical_outcome_p10_pct'])} % à {value(p['historical_outcome_p90_pct'])} % |")
    lines += ['', '## Couverture du test et erreurs de direction', '',
        '| Horizon | Requêtes choisies | Estimation suffisante | Résultat après fin du fichier | Série incomplète | Hausses correctes | Fausses hausses | Hausses manquées | Absences de hausse correctes |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in report['evaluation_metrics']:
        lines.append(f"| {r['horizon_months']} mois | {r['selected_queries']} | {r['sufficient_analogue_queries']} | {r['outcomes_after_dataset_end']} | {r['outcomes_with_incomplete_series']} | {r['true_positive']} | {r['false_positive']} | {r['false_negative']} | {r['true_negative']} |")
    lines += ['', 'Une fréquence estimée de hausse au moins égale à 50 % classe le résultat comme hausse. Les résultats manquants ne sont pas comptés comme des baisses.', '']
    lines += ['', '## Portée et limites', '',
        'Règles fixées pour cette version : trois variations mensuelles successives, saison à ±1 mois, rapport de prix au moins 0,5, distance moyenne des variations logarithmiques au plus 0,10, vingt voisins maximum et dix références présumées minimum. Ces choix n’ont pas été optimisés ni validés pour la prévision.', '',
        'Les estimations, écarts et exemples sont archivés avec les mois et lignes sources dans trajectory_research.json.gz. Les fenêtres et marchés sont dépendants ; la disponibilité à l’époque des données, les variantes et la représentativité ne sont pas établies. La sélection des requêtes précède le contrôle de leurs résultats futurs.', '',
        '**Avantage prédictif non établi.** Aucun signal d’achat ou de revente actuel n’est émis.']
    return '\n'.join(lines) + '\n'


def main():
    cli = argparse.ArgumentParser(); cli.add_argument('--out', required=True); cli.add_argument('--cache', required=True)
    args = cli.parse_args(); out = Path(args.out); cache = Path(args.cache)/IMPORT_ID
    try:
        imported = json.loads((out/'monthly_history.json').read_text())
        if imported['status'] != 'IMPORTED_NATIVE_SCOPE' or imported['source_sha256'] != SHA256:
            raise ValueError('Verified monthly import unavailable')
        raw = (cache/'monthly_series.json.gz').read_bytes()
        if hashlib.sha256(raw).hexdigest() != imported['normalized_sha256']:
            raise ValueError('Normalized historical data checksum mismatch')
        dataset = json.loads(gzip.decompress(raw))
        if dataset['dataset_id'] != IMPORT_ID: raise ValueError('Unexpected dataset ID')
        episodes = build_episodes(dataset['series'])
        evaluations = evaluate(episodes)
        example = next((e for e in episodes if e['configuration']['source_url'] == 'https://promoklocki.pl/lego-icons-10312-klub-jazzowy-h22044'
                        and e['configuration']['anchor_month'] == '2023-06'), None)
        report = {'schema': 'edge.mri.monthly_trajectory_research.v1', 'status': 'RETROSPECTIVE_RESEARCH_COMPLETE',
            'generated_at': now(), 'method': 'FROZEN_RULES_CHRONOLOGICAL_MONTHLY_NEIGHBOURS_V1',
            'dataset_id': IMPORT_ID, 'source_sha256': SHA256, 'normalized_sha256': imported['normalized_sha256'],
            'market': 'PL', 'currency': 'PLN', 'aggregation': imported['aggregation'], 'episode_count': len(episodes),
            'evaluation_query_count': len(evaluations), 'evaluation_query_months': QUERY_MONTHS,
            'queries_per_month_max': QUERIES_PER_MONTH, 'minimum_samples': MIN_SAMPLE, 'maximum_neighbours': K,
            'point_in_time_backtest_validated': False, 'calibrated_for_future_prediction': False,
            'independence_verified': False, 'completed_sales_verified': False, 'buy_signal': False,
            'evaluation_metrics': metrics(evaluations),
            'fixed_example': {'configuration': example['configuration'], 'predictions': predict(example['configuration'], episodes)} if example else {},
            'rules': {'feature_months': 4, 'outcome_must_end_before_query_month': True,
                      'maximum_mean_absolute_log_change_distance': MAX_LOG_DISTANCE,
                      'minimum_price_ratio': .5, 'maximum_circular_calendar_month_distance': 1,
                      'product_grouping': 'CONSERVATIVE_URL_REFERENCE_HINT_NOT_OFFICIAL_VARIANT_ID',
                      'query_sampling': 'FIXED_SHA256_ORDER_BEFORE_INSPECTING_QUERY_FUTURE_OUTCOMES'},
            'evaluations': evaluations}
        audit = gzip.compress(json.dumps({k:v for k,v in report.items() if k != 'generated_at'}, sort_keys=True, ensure_ascii=False).encode(), mtime=0)
        (out/'trajectory_research.json.gz').write_bytes(audit)
        summary = {k:v for k,v in report.items() if k not in ('evaluations','fixed_example')}
        summary['audit_sha256'] = hashlib.sha256(audit).hexdigest()
        summary['fixed_example'] = {'configuration': report['fixed_example'].get('configuration'),
            'predictions': [{k:v for k,v in p.items() if k != 'matches'} for p in report['fixed_example'].get('predictions',[])]}
        (out/'trajectory_report.md').write_text(render(report))
    except Exception as exc:
        summary = {'schema': 'edge.mri.monthly_trajectory_research.v1', 'status': 'FAILED', 'error': str(exc)[:300], 'buy_signal': False}
        (out/'trajectory_report.md').write_text('# EDGE — Analyse mensuelle indisponible\n\n' + summary['error'] + '\n')
    (out/'trajectory_summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(json.dumps({k:v for k,v in summary.items() if k in ('status','error','episode_count','evaluation_query_count','evaluation_metrics')}))


if __name__ == '__main__': main()
