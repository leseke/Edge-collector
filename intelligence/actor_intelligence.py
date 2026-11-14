"""EDGE MRI-002: Public actor events and competing market hypotheses. No investment authority."""
from datetime import datetime, timezone
from hashlib import sha256
import json

ACTOR_TYPES = {'brand', 'marketplace', 'publisher', 'creator', 'community', 'retailer', 'other'}
ACTION_TYPES = {'publication', 'launch', 'reprint', 'promotion', 'delisting', 'price_change', 'policy_change', 'other'}
HYPOTHESES = {'demand_growth', 'supply_shock', 'attention_only', 'strategic_promotion', 'uncertain'}

def _time(value):
    if not isinstance(value, str):
        raise ValueError('timestamp required')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('timezone required')
    return dt.astimezone(timezone.utc)

def _text(value):
    return isinstance(value, str) and 0 < len(value.strip()) <= 2000

def validate_actor(actor):
    if not isinstance(actor, dict) or not all(k in actor for k in ('actor_id', 'name', 'actor_type')):
        raise ValueError('actor invalid')
    if not _text(actor['actor_id']) or not _text(actor['name']) or actor['actor_type'] not in ACTOR_TYPES:
        raise ValueError('actor invalid')
    if any(k in actor for k in ('personal_profile', 'private_contact', 'political_affiliation', 'financial_decision')):
        raise ValueError('private or financial content forbidden')
    return actor

def validate_action(action):
    required = ('event_id','actor_id','subject_id','action_type','occurred_at','observed_at','source_id','summary')
    if not isinstance(action, dict) or any(k not in action for k in required):
        raise ValueError('action invalid')
    if any(not _text(action[k]) for k in ('event_id','actor_id','subject_id','source_id','summary')) or action['action_type'] not in ACTION_TYPES:
        raise ValueError('action invalid')
    if _time(action['occurred_at']) > _time(action['observed_at']):
        raise ValueError('observation before occurrence')
    if any(k in action for k in ('decision','allocation','capital','BUY','STRONG_BUY')):
        raise ValueError('finance forbidden')
    return action

def build_actor_brief(actor, actions, *, as_of):
    """Use only events known at as_of; do not infer private motivations."""
    validate_actor(actor)
    cutoff = _time(as_of)
    accepted = []
    for a in actions:
        validate_action(a)
        if a['actor_id'] != actor['actor_id']:
            continue
        if _time(a['observed_at']) <= cutoff and _time(a['occurred_at']) <= cutoff:
            accepted.append({k:a[k] for k in ('event_id','actor_id','subject_id','action_type','occurred_at','observed_at','source_id','summary')})
    accepted.sort(key=lambda x:(x['occurred_at'],x['event_id']))
    if len({a['event_id'] for a in accepted}) != len(accepted):
        raise ValueError('duplicate event')
    return {'actor':{k:actor[k] for k in ('actor_id','name','actor_type')},'as_of':as_of,
            'known_actions':accepted,'motives_observed':False,'inferred_intent':'unknown'}

def propose_scenarios(brief, thesis, rival, *, mechanism, supporting_event_ids, counter_event_ids, falsifiers, horizon_days):
    """Build testable alternatives using only known event IDs."""
    if not isinstance(brief,dict) or 'known_actions' not in brief:
        raise ValueError('brief required')
    if thesis not in HYPOTHESES or rival not in HYPOTHESES or thesis == rival:
        raise ValueError('two distinct hypotheses required')
    if not _text(mechanism) or not isinstance(horizon_days,int) or isinstance(horizon_days,bool) or not 1 <= horizon_days <= 365:
        raise ValueError('invalid mechanism or horizon')
    if not isinstance(falsifiers,list) or not falsifiers or any(not _text(f) for f in falsifiers):
        raise ValueError('falsifiers required')
    known = {a['event_id'] for a in brief['known_actions']}
    if not isinstance(supporting_event_ids,list) or not isinstance(counter_event_ids,list):
        raise ValueError('event ids required')
    if not set(supporting_event_ids+counter_event_ids).issubset(known):
        raise ValueError('future/unknown evidence forbidden')
    if any(not _text(x) for x in supporting_event_ids+counter_event_ids):
        raise ValueError('invalid evidence id')
    item={'actor_id':brief['actor']['actor_id'],'as_of':brief['as_of'],'thesis':thesis,'rival':rival,
          'mechanism':mechanism,'supporting_event_ids':sorted(set(supporting_event_ids)),
          'counter_event_ids':sorted(set(counter_event_ids)),'falsifiers':list(falsifiers),
          'horizon_days':horizon_days,'inference_status':'unverified',
          'causality':'not_established','policy_decision':'NOT_EVALUATED'}
    item['hypothesis_id']=sha256(json.dumps(item,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:20]
    return item
