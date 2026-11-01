"""Immutable, timestamped retail forecasts and separate source-linked follow-up."""
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
from statistics import mean

from announcement_history import timestamp
from commercial_history import now


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def model_signature():
    root = Path(__file__).parent
    files = {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
             ('analogue_history.py', 'commercial_reaction_history.py', 'probability_history.py', 'forecast_history.py')}
    return {'id': digest(files), 'source_sha256': files, 'target': 'SOURCE_DECLARED_IN_STOCK_AT_TARGET_CAPTURE_WITHIN_SIX_HOURS',
            'calibrated_for_future_prediction': False}


def checked_records(reports, at):
    records = {}
    for report in reports:
        if report.get('schema') != 'edge.mri.frozen_forecasts.v1': raise ValueError('Unexpected forecast ledger schema')
        for row in report['records']:
            content = {k:v for k,v in row.items() if k != 'record_sha256'}
            if digest(content) != row.get('record_sha256'): raise ValueError('Forecast record checksum mismatch')
            identity = digest([row['model']['id'], row['event_id'], row['horizon_hours']])
            if identity != row['id']: raise ValueError('Forecast identity mismatch')
            if not timestamp(row['created_at']) or timestamp(row['created_at']) > timestamp(at):
                raise ValueError('Forecast issuance timestamp is invalid or future dated')
            if identity in records and records[identity] != row:
                raise ValueError('Conflicting immutable forecast replays')
            records[identity] = row
    return records


def freeze(analogue, previous, at, model):
    records = checked_records(previous, at)
    created, reused = 0, 0
    if not timestamp(analogue.get('generated_at')) or timestamp(analogue['generated_at']) > timestamp(at):
        raise ValueError('Analogue report is not known at issuance time')
    for q in analogue['queries']:
        config = q['configuration']; anchor = timestamp(config['as_of'])
        if anchor is None or anchor > timestamp(at): raise ValueError('Query configuration is future dated')
        if not config['evidence'] or any(timestamp(e['observed_at']) is None or timestamp(e['observed_at']) > anchor for e in config['evidence']):
            raise ValueError('Feature evidence is missing or future dated')
        for h in q['horizons']:
            identity = digest([model['id'], q['event_id'], h['horizon_hours']])
            if identity in records:
                reused += 1
                continue  # Never replace the first issued forecast with a later recomputation.
            trials = []; products = set()
            for match in h['analogues']:
                w = match['measured_outcome']
                if w.get('availability') not in ('IN_STOCK','OUT_OF_STOCK'): continue
                if (w.get('status') != 'MEASURED' or w.get('horizon_hours') != h['horizon_hours']
                        or not timestamp(w.get('observed_at')) or timestamp(w['observed_at']) > anchor
                        or match['product_id'] == q['product_id'] or match['product_id'] in products
                        or not w.get('evidence_sha256')):
                    raise ValueError('Invalid, repeated or future analogue outcome')
                products.add(match['product_id']); trials.append(match)
            n = len(trials); hits = sum(m['measured_outcome']['availability'] == 'IN_STOCK' for m in trials)
            enough = n >= h['minimum_samples'] and h['minimum_samples'] >= 5
            expected = hits/n if enough else None
            probability = h['estimated_in_stock_frequency']
            if (n != h['sample_count'] or hits != h['in_stock_count'] or (probability is None) != (expected is None)
                    or (expected is not None and (not math.isfinite(probability) or abs(probability-expected) > 1e-12))):
                raise ValueError('Forecast probability does not match its measured sample')
            target = anchor + dt.timedelta(hours=h['horizon_hours'])
            prospective = timestamp(at) < target
            row = {'id': identity, 'model': model, 'event_id': q['event_id'], 'product_id': q['product_id'],
                'created_at': at, 'feature_as_of': config['as_of'], 'configuration': config,
                'horizon_hours': h['horizon_hours'], 'target_at': target.isoformat(),
                'window_end': (target+dt.timedelta(hours=6)).isoformat(),
                'registration_timing': 'BEFORE_TARGET' if prospective else 'LATE_REGISTRATION',
                'estimate_status': 'ESTIMATE' if probability is not None else 'ABSTAIN_INSUFFICIENT_HISTORY',
                'estimated_in_stock_probability': probability, 'sample_count': n,
                'eligible_for_prospective_scoring': prospective and probability is not None,
                'baseline_in_stock_probability': 0 if config['family'] == 'OBSERVED_STOCKOUT' else 1 if config['family'] == 'OBSERVED_RESTOCK' else None,
                'analogue_evidence': h, 'input_report_sha256': digest(analogue),
                'data_kind': 'COMPUTED_ESTIMATE_OR_EXPLICIT_ABSTENTION', 'buy_signal': False}
            row['record_sha256'] = digest(row)
            records[identity] = row; created += 1
    return {'schema': 'edge.mri.frozen_forecasts.v1', 'generated_at': at,
            'records': sorted(records.values(), key=lambda r:(r['created_at'],r['id'])),
            'created_this_run': created, 'reused_this_run': reused,
            'policy': 'FIRST_ISSUANCE_PER_MODEL_EVENT_HORIZON_IS_IMMUTABLE'}


def evaluate(ledger, followup, at):
    events = {e['id']:e for e in followup['events']}
    rows = []
    for r in ledger['records']:
        event = events.get(r['event_id'])
        w = next((w for w in event['windows'] if w['horizon_hours'] == r['horizon_hours']),None) if event else None
        result = {'forecast_id':r['id'], 'record_sha256':r['record_sha256'], 'model_id':r['model']['id'],
            'product_id':r['product_id'], 'horizon_hours':r['horizon_hours'], 'target_at':r['target_at'],
            'estimate_status':r['estimate_status'], 'registration_timing':r['registration_timing'],
            'outcome_status':w['status'] if w else 'EVENT_EVIDENCE_UNAVAILABLE',
            'validation_status':'NOT_YET_SCORABLE', 'brier_score':None, 'baseline_brier_score':None}
        if event and (event['product_id'] != r['product_id'] or event['seller'] != r['configuration']['seller']
                or event['currency'] != r['configuration']['currency']
                or event['source_url'] not in {e['url'] for e in r['configuration']['evidence']}):
            raise ValueError('Outcome source or product scope changed')
        if w and w['status'] == 'MEASURED':
            stamp = timestamp(w.get('observed_at'))
            if (not stamp or not timestamp(r['target_at']) <= stamp <= timestamp(r['window_end'])
                    or stamp > timestamp(at) or not w.get('evidence_sha256')
                    or timestamp(w['target_at']) != timestamp(r['target_at'])):
                raise ValueError('Outcome outside forecast scope or observation window')
            result['observed_outcome'] = dict(w, source_url=event['source_url'], seller=event['seller'], currency=event['currency'])
            if w['availability'] not in ('IN_STOCK','OUT_OF_STOCK'):
                result['validation_status'] = 'UNKNOWN_TARGET_AVAILABILITY'
            elif r['estimate_status'] != 'ESTIMATE':
                result['validation_status'] = 'OBSERVED_AFTER_ABSTENTION_NOT_A_PREDICTION'
            elif not r['eligible_for_prospective_scoring']:
                result['validation_status'] = 'EXCLUDED_LATE_REGISTRATION'
            else:
                actual = int(w['availability'] == 'IN_STOCK')
                result.update(validation_status='SCORED_PROSPECTIVE',
                    brier_score=(r['estimated_in_stock_probability']-actual)**2,
                    baseline_brier_score=(r['baseline_in_stock_probability']-actual)**2 if r['baseline_in_stock_probability'] is not None else None)
        rows.append(result)
    metrics = []
    for model in sorted({r['model_id'] for r in rows}):
        for h in (24,72,168):
            group = [r for r in rows if r['model_id']==model and r['horizon_hours']==h]
            scored = [r for r in group if r['validation_status']=='SCORED_PROSPECTIVE']
            paired = [r for r in scored if r['baseline_brier_score'] is not None]
            metrics.append({'model_id':model,'horizon_hours':h,'records':len(group),'scored_count':len(scored),
                'abstentions':sum(r['estimate_status']!='ESTIMATE' for r in group),
                'late_registrations':sum(r['registration_timing']=='LATE_REGISTRATION' for r in group),
                'missing_target_captures':sum(r['outcome_status']=='MISSING_WINDOW_OBSERVATION' for r in group),
                'brier_score':mean(r['brier_score'] for r in scored) if scored else None,
                'paired_baseline_count':len(paired),
                'paired_brier_score':mean(r['brier_score'] for r in paired) if paired else None,
                'baseline_brier_score':mean(r['baseline_brier_score'] for r in paired) if paired else None,
                'calibration_validated':False,'independence_verified':False})
    return {'schema':'edge.mri.prospective_followup.v1','generated_at':at,'evaluations':rows,'metrics':metrics,
            'calibrated_for_future_prediction':False,'profitability_measured':False}


def render(ledger, report):
    lines=['# EDGE — Registre des estimations figées', '',
        'Chaque estimation ou abstention conserve sa date réelle de production, les preuves et la version du modèle. Une inscription après la date cible est exclue des scores prospectifs. Les rapports rétrospectifs mensuels ne sont pas des prévisions réelles.', '',
        '| Produit | Horizon | Date cible UTC | Inscription | Estimation | Résultat suivi |', '|---|---:|---|---|---|---|']
    records={r['id']:r for r in ledger['records']}
    for e in report['evaluations']:
        r=records[e['forecast_id']]
        p=r['estimated_in_stock_probability']; label='Abstention : données insuffisantes' if p is None else f'{p*100:.1f} % (estimation)'
        lines.append(f"| {r['product_id']} | {r['horizon_hours']} h | {r['target_at']} | {r['registration_timing']} à {r['created_at']} | {label} | {e['outcome_status']} |")
    lines += ['', '## Scores prospectifs', '', '| Modèle | Horizon | Prévisions évaluées | Score de Brier | Référence persistance | Captures cibles manquantes |', '|---|---:|---:|---|---|---:|']
    for m in report['metrics']:
        score='Non calculé' if m['brier_score'] is None else f"{m['brier_score']:.4f}"
        base='Non calculé' if m['baseline_brier_score'] is None else f"{m['baseline_brier_score']:.4f}"
        lines.append(f"| {m['model_id'][:12]} | {m['horizon_hours']} h | {m['scored_count']} | {score} | {base} | {m['missing_target_captures']} |")
    lines += ['', 'Une capture manquante ou une abstention ne devient jamais un échec de prévision. Une absence de variation de prix ne prouve pas une absence de réassort entre les relevés. Les prix affichés et disponibilités déclarées ne prouvent ni vente conclue ni marge. Calibration future et avantage prédictif restent non établis.']
    return '\n'.join(lines)+'\n'


def main():
    cli=argparse.ArgumentParser();cli.add_argument('--out',required=True);cli.add_argument('--history',required=True)
    args=cli.parse_args();out,root=Path(args.out),Path(args.history)
    previous=[json.loads(p.read_text()) for p in sorted(root.glob('*/forecast_records.json'))]
    analogue=json.loads((out/'analogue_matches.json').read_text())
    followup=json.loads((out/'commercial_reactions.json').read_text())
    at=now();ledger=freeze(analogue,previous,at,model_signature());report=evaluate(ledger,followup,at)
    (out/'forecast_records.json').write_text(json.dumps(ledger,indent=2,ensure_ascii=False))
    (out/'forecast_evaluations.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    (out/'forecast_report.md').write_text(render(ledger,report))
    print(json.dumps({'records':len(ledger['records']),'created':ledger['created_this_run'],
        'prospective_scores':sum(m['scored_count'] for m in report['metrics'])}))


if __name__=='__main__':main()
