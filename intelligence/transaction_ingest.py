"""AI-002E — supervised, offline transaction intake, not a sold-price scraper.

An import is a candidate until the human has reviewed the original platform sale
or receipt. There is no decision field and no automatic verification promotion.
"""
import hashlib
import json
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from intelligence.evidence import _append_line

SCHEMA = 'edge.transaction_candidate.v1'


def validate_candidate(item):
    if not isinstance(item, dict):
        raise ValueError('transaction candidate must be an object')
    allowed = {'product_id', 'marketplace', 'sold_at', 'price', 'currency', 'territory',
               'evidence_url', 'evidence_kind', 'observed_at', 'source_method', 'notes'}
    if set(item) - allowed:
        raise ValueError('unexpected fields (including financial decisions)')
    required = allowed - {'notes'}
    if not required.issubset(item):
        raise ValueError('missing required fields')
    for key in ('product_id', 'marketplace', 'currency', 'territory', 'source_method'):
        if not isinstance(item[key], str) or not item[key].strip():
            raise ValueError('missing or invalid '+key)
    if item['source_method'] not in ('manual_review', 'licensed_api_export'):
        raise ValueError('unsupported collection method')
    if item['evidence_kind'] not in ('platform_sold_record', 'receipt'):
        raise ValueError('a listing or seller claim is not a completed transaction')
    p = urlsplit(str(item['evidence_url']))
    if p.scheme != 'https' or not p.hostname or p.username or p.password:
        raise ValueError('valid HTTPS evidence URL required')
    if len(item['currency']) != 3 or not item['currency'].isalpha() or item['currency'] != item['currency'].upper():
        raise ValueError('ISO-style currency code required')
    try:
        amount = Decimal(str(item['price']))
    except (InvalidOperation, ValueError):
        raise ValueError('invalid price')
    if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
        raise ValueError('positive price with <=2 decimals required')
    try:
        sold = datetime.fromisoformat(item['sold_at'].replace('Z', '+00:00'))
        observed = datetime.fromisoformat(item['observed_at'].replace('Z', '+00:00'))
        if sold.tzinfo is None or observed.tzinfo is None or sold > observed:
            raise ValueError('timestamp ordering or timezone invalid')
    except (TypeError, AttributeError):
        raise ValueError('invalid timestamps')
    if not isinstance(item.get('notes', ''), str):
        raise ValueError('invalid notes')
    return True


def prepare_candidate(item):
    validate_candidate(item)
    normalized = dict(item)
    normalized['price'] = format(Decimal(str(item['price'])), '.2f')
    normalized.setdefault('notes', '')
    raw = json.dumps(normalized, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return {'schema': SCHEMA, 'candidate_id': hashlib.sha256(raw.encode()).hexdigest(),
            'status': 'unverified', 'review': 'human_review_required', 'data': normalized,
            'warning': 'Supplied URL is not proof that a transaction actually occurred; do not chart as confirmed sale.'}


def import_candidates(path, entries):
    """Only writes a local append-only *unverified* candidate ledger. No network."""
    candidates = [prepare_candidate(i) for i in entries]  # validate all before write
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    seen = set()
    if os.path.isfile(path):
        with open(path, encoding='utf-8') as handle:
            for line in handle:
                if line.strip():
                    try:
                        previous = json.loads(line)
                        seen.add(previous.get('candidate_id'))
                    except json.JSONDecodeError:
                        raise ValueError('ledger damaged; manual repair required before append')
    count = 0
    for entry in candidates:
        if entry['candidate_id'] not in seen:
            _append_line(path, json.dumps(entry, sort_keys=True, ensure_ascii=False))
            seen.add(entry['candidate_id'])
            count += 1
    return count
