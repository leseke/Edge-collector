"""Labelled empirical estimates from measured reaction windows, never invented observations."""
import argparse
import json
import math
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import median
from announcement_history import timestamp
from commercial_history import now


def wilson(successes, n):
    z = 1.959963984540054
    p = successes / n
    scale = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / scale
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / scale
    return [max(0, centre - half), min(1, centre + half)]


def estimate(reports, product_by_observation, minimum_samples=5):
    # Replaying snapshots does not add trials. Multiple sources/sellers for one
    # product/event day do not become separate Bernoulli trials.
    grouped = {}
    for report in reports:
        for measurement in report.get('measurements', []):
            product = product_by_observation.get(measurement.get('observation_id'))
            anchor = timestamp(measurement.get('anchor'))
            if not product or not anchor:
                continue
            for window in measurement.get('windows', []):
                if window.get('status') != 'MEASURED':
                    continue
                try:
                    change = Decimal(str(window['asking_price_change_pct']))
                except (KeyError, InvalidOperation):
                    continue
                if not change.is_finite():
                    continue
                horizon = window['horizon_hours']
                key = (product, anchor.date().isoformat(), horizon)
                evidence_key = (window.get('before_evidence_sha256'), window.get('after_evidence_sha256'),
                                measurement.get('observation_id'), window.get('after_observed_at'))
                grouped.setdefault(key, {})[evidence_key] = change
    result = []
    for horizon in (24, 72, 168):
        trials = [(key, median(values.values())) for key, values in grouped.items() if key[2] == horizon]
        n = len(trials)
        successes = sum(change > 0 for _, change in trials)
        enough = n >= minimum_samples
        result.append({'horizon_hours': horizon, 'sample_count': n, 'positive_change_count': successes,
            'minimum_samples': minimum_samples,
            'status': 'ESTIMATED_HISTORICAL_FREQUENCY' if enough else 'INSUFFICIENT_MEASURED_SAMPLE',
            'estimated_probability': successes / n if enough else None,
            'binomial_reference_interval_95': wilson(successes, n) if enough else None,
            'sample_units': [{'product_id': key[0], 'event_day_utc': key[1]} for key, _ in trials],
            'calibrated_for_future_prediction': False, 'independence_verified': False})
    return {'schema': 'edge.mri.probability_estimates.v1', 'generated_at': now(),
        'data_kind': 'COMPUTED_ESTIMATE_NOT_OBSERVED_FACT',
        'method': 'DEDUPLICATED_EMPIRICAL_FREQUENCY_WITH_WILSON_BINOMIAL_REFERENCE_INTERVAL_V1',
        'target': 'POSITIVE_MEDIAN_ASKING_PRICE_CHANGE_AFTER_TRACKED_PUBLICATION',
        'trial_unit': 'PRODUCT_AND_PUBLICATION_UTC_DAY_AND_HORIZON',
        'interval_limitations': 'Binomial reference assumes independent trials; dependence is not verified and limits interpretation.',
        'not_a_probability_of': ['profit', 'completed sale', 'causal impact'], 'estimates': result}


def render(report):
    lines = ['# EDGE — Estimations calculées séparément des faits', '',
        'Mesure : fréquence historique de hausse du prix affiché médian autour des publications suivies. Elle ne mesure ni le bénéfice, ni une vente conclue, ni un effet causal.', '',
        '| Horizon | Épisodes mesurés distincts | Hausses observées | Estimation calculée |', '|---|---:|---:|---|']
    for row in report['estimates']:
        value = 'Données insuffisantes' if row['estimated_probability'] is None else f"{100 * row['estimated_probability']:.1f} %"
        lines.append(f"| {row['horizon_hours']} h | {row['sample_count']} | {row['positive_change_count']} | {value} |")
    lines += ['', 'Méthode : fréquence empirique, au moins cinq épisodes produit/jour/horizon. Les captures répétées sont dédupliquées.', '',
        'Les intervalles binomiaux sont indicatifs : l’indépendance des épisodes reste non vérifiée. Aucune calibration prédictive future n’est établie.']
    return '\n'.join(lines) + '\n'


def main():
    cli = argparse.ArgumentParser();cli.add_argument('--out', required=True);cli.add_argument('--history', required=True)
    args = cli.parse_args();out, root = Path(args.out), Path(args.history)
    reports, mapping = [], {}
    for folder in list(root.glob('*')) + [out]:
        path = folder / 'report.json'
        if path.exists():
            for row in json.loads(path.read_text()).get('observations', []):
                mapping[row['id']] = row['product_id']
        path = folder / 'reactions.json'
        if path.exists(): reports.append(json.loads(path.read_text()))
    report = estimate(reports, mapping)
    (out / 'probabilities.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
    (out / 'probability_report.md').write_text(render(report))
    print(json.dumps({'probability_sample_counts': [r['sample_count'] for r in report['estimates']],
                      'numeric_estimates': sum(r['estimated_probability'] is not None for r in report['estimates'])}))


if __name__ == '__main__': main()
