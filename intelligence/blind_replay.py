"""MRI-002 historical blind replay: enforce a time cut and a frozen, rival hypothesis.

Does not claim predictive validity until independent historical datasets are supplied.
"""
from hashlib import sha256
import json
from intelligence.actor_intelligence import build_actor_brief, propose_scenarios, _time
from intelligence.market_reaction import snapshot, assess_prediction


def freeze_case(actor, actions, market_events, measurements, *, as_of, thesis,
                rival, mechanism, supporting_event_ids, counter_event_ids,
                falsifiers, horizon_days, prediction):
    """Freeze everything visible at as_of before outcome observations are evaluated."""
    brief = build_actor_brief(actor, actions, as_of=as_of)
    known = snapshot(market_events, measurements, as_of)
    proposed = propose_scenarios(
        brief, thesis, rival, mechanism=mechanism,
        supporting_event_ids=supporting_event_ids,
        counter_event_ids=counter_event_ids,
        falsifiers=falsifiers, horizon_days=horizon_days)
    if not isinstance(prediction, dict) or set(prediction) != {'metric', 'direction', 'by_days'}:
        raise ValueError('exactly one structured prediction required')
    if prediction['by_days'] != horizon_days:
        raise ValueError('prediction horizon mismatch')
    subject_ids = {a['subject_id'] for a in brief['known_actions']}
    candidates = [e for e in known['events'] if e['id'] in supporting_event_ids]
    if not candidates or not all(e['subject_id'] in subject_ids for e in candidates):
        raise ValueError('a known MRI event matching supporting evidence is required')
    event = sorted(candidates, key=lambda x: x['occurred_at'])[0]
    from intelligence.market_reaction import make_hypothesis
    mri_hyp = make_hypothesis(event, mechanism, rival, [prediction],
                              '; '.join(falsifiers), 'No financial conclusion')
    frozen = {'as_of': as_of, 'actor_brief': brief, 'hypothesis': proposed,
              'mri_hypothesis': mri_hyp, 'event': event,
              'known_measure_ids': [m['id'] for m in known['measures']],
              'schema': 'edge.mri.blind_replay.v1',
              'status': 'FROZEN_UNVERIFIED'}
    frozen['seal_sha256'] = sha256(json.dumps(frozen, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return frozen


def evaluate_frozen(frozen, measurements, *, as_of):
    """Evaluate later outcomes without mutating a frozen thesis."""
    if _time(as_of) < _time(frozen['as_of']):
        raise ValueError('cannot evaluate before frozen cutoff')
    content = {k:v for k,v in frozen.items() if k != 'seal_sha256'}
    if sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest() != frozen['seal_sha256']:
        raise ValueError('frozen thesis altered')
    outcome = assess_prediction(frozen['mri_hypothesis'], frozen['event'], measurements, as_of)
    return {'seal_sha256': frozen['seal_sha256'], 'evaluated_at': as_of,
            'outcomes': outcome['outcomes'], 'causality': 'not_established',
            'source_quality': 'not_assessed', 'forecast_skill': 'not_established'}
