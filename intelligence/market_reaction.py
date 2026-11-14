"""EDGE MRI-001: intelligence événementielle, interprétation prudente et rejeu anti-fuite.

Aucune API, I/O réseau, LLM, allocation ou décision BUY dans ce module.
Les scores éventuels sont des mesures descriptives, jamais des probabilités.
"""
from datetime import datetime, timezone
from statistics import median
import json

VERSION = 'edge.market_reaction.v1'
ALLOWED = {'publication', 'launch', 'reprint', 'price_change', 'stock_change', 'community_signal', 'listing_change', 'other'}
METRICS = {'mentions', 'search_interest', 'sold_count', 'sold_median', 'asking_median', 'availability', 'engagement'}


def instant(value):
    if not isinstance(value, str):
        raise ValueError('timestamp ISO requis')
    d = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if d.tzinfo is None:
        raise ValueError('timezone obligatoire')
    return d.astimezone(timezone.utc)


def _require_fields(d, required):
    if not isinstance(d, dict) or not all(k in d for k in required):
        raise ValueError('champs requis absents')


def validate_event(event):
    _require_fields(event, ('id', 'actor', 'kind', 'occurred_at', 'observed_at', 'source_id', 'summary', 'subject_id'))
    if event['kind'] not in ALLOWED or any(not isinstance(event[k], str) or not event[k].strip() for k in ('id', 'actor', 'source_id', 'summary', 'subject_id')):
        raise ValueError('événement invalide')
    if instant(event['occurred_at']) > instant(event['observed_at']):
        raise ValueError('observation antérieure à événement')
    for k in ('BUY', 'STRONG_BUY', 'allocation', 'capital', 'decision'):
        if k in event:
            raise ValueError('champ financier interdit')
    return event


def validate_measure(measure):
    _require_fields(measure, ('id', 'subject_id', 'metric', 'value', 'measured_at', 'observed_at', 'source_id', 'method'))
    if measure['metric'] not in METRICS:
        raise ValueError('métrique inconnue')
    if not isinstance(measure['value'], (int, float)) or isinstance(measure['value'], bool) or not (-1e100 < measure['value'] < 1e100):
        raise ValueError('mesure non numérique finie')
    if instant(measure['measured_at']) > instant(measure['observed_at']):
        raise ValueError('mesure du futur par rapport à observation')
    if measure['metric'] in {'sold_count', 'sold_median'} and measure.get('evidence_kind') != 'verified_sale':
        raise ValueError('vente réalisée sans statut de preuve')
    for k in ('decision', 'allocation', 'capital'):
        if k in measure:
            raise ValueError('décision financière interdite')
    return measure


def snapshot(events, measures, as_of):
    """Filtrer sur date de *connaissance*, pas seulement date d'événement.

    Refuse toute réutilisation d'informations connues après as_of, même si datées avant.
    """
    cut = instant(as_of)
    ev = [validate_event(e) for e in events]
    ms = [validate_measure(m) for m in measures]
    eout = sorted((dict(e) for e in ev if instant(e['observed_at']) <= cut and instant(e['occurred_at']) <= cut), key=lambda x: (x['occurred_at'], x['id']))
    mout = sorted((dict(m) for m in ms if instant(m['observed_at']) <= cut and instant(m['measured_at']) <= cut), key=lambda x: (x['measured_at'], x['id']))
    if len({e['id'] for e in eout}) != len(eout) or len({m['id'] for m in mout}) != len(mout):
        raise ValueError('identifiant dupliqué')
    return {'as_of': as_of, 'events': eout, 'measures': mout}


def make_hypothesis(event, mechanism, rival, predictions, invalidate_if, risks):
    """Hypothèses humaines ou IA comme propositions non vérifiées, sans génération cachée."""
    validate_event(event)
    for name, val in [('mechanism', mechanism), ('rival', rival), ('invalidate_if', invalidate_if), ('risks', risks)]:
        if not isinstance(val, str) or not val.strip():
            raise ValueError(f'{name} requis')
    if not isinstance(predictions, list) or not predictions:
        raise ValueError('prédictions requises')
    clean=[]
    for p in predictions:
        _require_fields(p, ('metric', 'direction', 'by_days'))
        if p['metric'] not in METRICS or p['direction'] not in ('increase','decrease','flat') or not isinstance(p['by_days'], int) or p['by_days'] <= 0:
            raise ValueError('prédiction invalide')
        clean.append(dict(p))
    return {'event_id': event['id'], 'subject_id': event['subject_id'], 'mechanism': mechanism,
            'rival_explanation': rival, 'predictions': clean, 'invalidate_if': invalidate_if,
            'risk_factors': risks, 'verification': 'hypothesis_unverified', 'policy_decision': 'NOT_EVALUATED'}


def event_window(event, measures, as_of, metric, before_days=7, after_days=7):
    """Stats descriptives avant/après : rien n'est extrapolé ni causalement attribué."""
    from datetime import timedelta
    validate_event(event)
    if metric not in METRICS or before_days <= 0 or after_days <= 0:
        raise ValueError('fenêtre invalide')
    cut = instant(as_of)
    t = instant(event['occurred_at'])
    eligible = snapshot([event], measures, as_of)['measures']
    relevant = [m for m in eligible if m['subject_id']==event['subject_id'] and m['metric']==metric]
    before = [m for m in relevant if t-timedelta(days=before_days) <= instant(m['measured_at']) < t]
    after = [m for m in relevant if t < instant(m['measured_at']) <= min(t+timedelta(days=after_days), cut)]
    def summarize(items):
        return {'n':len(items), 'median':median(x['value'] for x in items) if items else None, 'ids':[x['id'] for x in items]}
    b,a=summarize(before), summarize(after)
    return {'event_id':event['id'], 'metric':metric, 'as_of':as_of, 'before':b, 'after':a,
            'delta_median':a['median']-b['median'] if a['median'] is not None and b['median'] is not None else None,
            'causality':'not_established', 'coverage':'observed_only',
            'warning':'Des variations ne prouvent ni causalité ni prévisibilité.'}


def assess_prediction(hypothesis, event, measures, as_of):
    """Évaluation prospective : une prédiction ne peut être évaluée avant sa fin de fenêtre."""
    from datetime import timedelta
    if hypothesis['event_id'] != event['id']:
        raise ValueError('hypothèse/événement incohérents')
    answers=[]
    for p in hypothesis['predictions']:
        maturity = instant(event['occurred_at']) + timedelta(days=p['by_days'])
        if instant(as_of) < maturity:
            answers.append({'metric':p['metric'], 'result':'PENDING'})
            continue
        window=event_window(event, measures, as_of, p['metric'], after_days=p['by_days'])
        delta=window['delta_median']
        if delta is None:
            result='NO_DATA'
        else:
            result='SUPPORTED' if ((p['direction']=='increase' and delta>0) or (p['direction']=='decrease' and delta<0) or (p['direction']=='flat' and delta==0)) else 'NOT_SUPPORTED'
        answers.append({'metric':p['metric'], 'result':result, 'delta':delta, 'evidence_ids':window['before']['ids']+window['after']['ids']})
    return {'event_id':event['id'], 'as_of':as_of, 'outcomes':answers, 'causality':'not_established'}
