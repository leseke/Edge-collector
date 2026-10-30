"""Bounded public offer observations; no purchase or messaging side effects."""
import argparse
import datetime as dt
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlsplit


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


class LD(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.buffer = []
        self.docs = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.active = dict(attrs).get('type', '').lower() == 'application/ld+json'
            self.buffer = []

    def handle_data(self, data):
        if self.active:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag == 'script' and self.active:
            try:
                self.docs.append(json.loads(''.join(self.buffer)))
            except ValueError:
                pass
            self.active = False


def nodes(value):
    if isinstance(value, list):
        for child in value:
            yield from nodes(child)
    elif isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)


def parse_offer(raw, target):
    parser = LD()
    parser.feed(raw.decode('utf-8'))
    offers = []
    for product in nodes(parser.docs):
        types = product.get('@type', [])
        if isinstance(types, str):
            types = [types]
        if 'Product' not in types:
            continue
        identity = ' '.join(str(product.get(k, '')) for k in ('sku', 'mpn', 'productID', 'name'))
        if not re.search(r'(?<!\d)' + re.escape(target['sku']) + r'(?!\d)', identity):
            continue
        data = product.get('offers', [])
        if isinstance(data, dict):
            data = [data]
        for offer in data:
            if not isinstance(offer, dict) or offer.get('@type') not in ('Offer', 'https://schema.org/Offer'):
                continue
            if target.get('expected_offer_seller'):
                seller = offer.get('seller', {})
                if not isinstance(seller, dict) or seller.get('name') != target['expected_offer_seller']:
                    continue
            try:
                price = Decimal(str(offer['price']))
            except (KeyError, InvalidOperation):
                continue
            currency = offer.get('priceCurrency')
            if not price.is_finite() or price <= 0 or currency != 'EUR':
                continue
            availability = str(offer.get('availability', '')).rsplit('/', 1)[-1]
            availability = {'InStock': 'IN_STOCK', 'OutOfStock': 'OUT_OF_STOCK',
                            'PreOrder': 'PREORDER', 'BackOrder': 'BACKORDER',
                            'Discontinued': 'DISCONTINUED', 'SoldOut': 'OUT_OF_STOCK'}.get(availability, 'UNKNOWN')
            offers.append({'price': str(price), 'currency': currency,
                           'availability': availability, 'product_name': product.get('name'),
                           'evidence': {'product': {k: product[k] for k in ('name', 'sku', 'mpn', 'productID') if k in product},
                                        'offer': offer}})
    if len(offers) != 1:
        raise ValueError('Expected exactly one identified EUR Offer; found ' + str(len(offers)))
    return offers[0]


def fetch(target, out):
    row = {'id': target['id'], 'product_id': target['product_id'], 'seller': target['seller'],
           'url': target['url'], 'observed_at': now(), 'status': 'FAILED',
           'price_kind': 'ASKING_PRICE', 'shipping_eur': None, 'completed_sale': False,
           'availability': 'UNKNOWN', 'purchase_authorized': False}
    row['source_qualification'] = target.get('source_qualification', 'NOT_ASSESSED')
    try:
        request = Request(target['url'], headers={'User-Agent': 'EDGE-MarketResearch/1.0', 'Accept': 'application/json' if target.get('adapter') == 'tcgdex' else 'text/html'})
        with urlopen(request, timeout=25) as response:
            row['http_status'] = response.status
            row['final_url'] = response.url
            if response.status != 200 or urlsplit(response.url).hostname != urlsplit(target['url']).hostname:
                raise ValueError('Unexpected status or redirect host')
            raw = response.read(3000001)
        if not raw or len(raw) > 3000000:
            raise ValueError('Invalid response size')
        row['body_sha256'] = digest(raw)
        row['raw_file'] = target['id'] + ('.json' if target.get('adapter') == 'tcgdex' else '.html')
        (out / row['raw_file']).write_bytes(raw)
        if target.get('adapter') == 'tcgdex':
            doc = json.loads(raw)
            if doc.get('id') != target['card_id']:
                raise ValueError('Card identity mismatch')
            pricing = doc.get('pricing', doc.get('prices', {})).get('cardmarket', {})
            price = Decimal(str(pricing.get('low')))
            if not price.is_finite() or price <= 0 or pricing.get('unit') != 'EUR':
                raise ValueError('Invalid indicative EUR low')
            row.update(price=str(price), currency='EUR', price_kind='AGGREGATED_INDICATIVE_LOW',
                       source_updated_at=pricing.get('updated'), sealed_product=False,
                       market_language_verified=False, evidence=pricing, status='OK')
        else:
            row.update(parse_offer(raw, target), status='OK')
    except Exception as exc:
        row['error_type'] = type(exc).__name__
        row['error'] = str(exc)[:200]
    return row


def prior_observations(row, current, history):
    return [(report['observed_at'], old) for report in history
            if report['observed_at'] < current['observed_at']
            for old in report['observations']
            if old['id'] == row['id'] and old['status'] == 'OK'
            and old['url'] == row['url'] and old['product_id'] == row['product_id']
            and old.get('price_kind') == row.get('price_kind')
            and old.get('seller') == row.get('seller')]


def comparison_report(current, history):
    rows = []
    for row in current['observations']:
        prior = prior_observations(row, current, history)
        item = {'id': row['id'], 'current_status': row['status'],
                'comparison_available': row['status'] == 'OK' and bool(prior)}
        if item['comparison_available']:
            stamp, old = max(prior, key=lambda pair: pair[0])
            item.update(previous_snapshot_at=stamp, previous_observed_at=old['observed_at'],
                        current_observed_at=row['observed_at'],
                        before_price=old['price'], after_price=row['price'],
                        before_availability=old['availability'], after_availability=row['availability'],
                        previous_evidence_sha256=old['body_sha256'],
                        current_evidence_sha256=row['body_sha256'],
                        price_kind=row.get('price_kind'))
            if old['currency'] == row['currency']:
                item['price_change_pct'] = str((Decimal(row['price']) / Decimal(old['price']) - 1) * 100)
        else:
            item['reason'] = 'CURRENT_COLLECTION_FAILED' if row['status'] != 'OK' else 'BASELINE_ONLY'
        rows.append(item)
    return {'schema': 'edge.commercial.comparisons.v1', 'observations': rows}


def compare(current, history):
    events = []
    for row in current['observations']:
        if row['status'] != 'OK':
            continue
        # Use last successful observation, preserving gaps and its actual timestamp.
        prior = prior_observations(row, current, history)
        if not prior:
            continue
        stamp, old = max(prior, key=lambda pair: pair[0])
        changes = []
        if old['currency'] == row['currency'] and Decimal(old['price']) != Decimal(row['price']):
            changes.append(('INDICATIVE_PRICE_CHANGE' if row.get('price_kind') == 'AGGREGATED_INDICATIVE_LOW' else 'PRICE_CHANGE', 'price', old['price'], row['price']))
        if 'UNKNOWN' not in (old['availability'], row['availability']) and old['availability'] != row['availability']:
            kind = 'RESTOCK_OBSERVED' if old['availability'] == 'OUT_OF_STOCK' and row['availability'] == 'IN_STOCK' else 'AVAILABILITY_CHANGE'
            changes.append((kind, 'availability', old['availability'], row['availability']))
        for kind, field, before, after in changes:
            event = {'kind': kind, 'observation_id': row['id'], 'product_id': row['product_id'],
                     'seller': row['seller'], 'field': field, 'before': before, 'after': after,
                     'window_start': old['observed_at'], 'window_end': row['observed_at'],
                     'previous_snapshot_at': stamp, 'source_url': row['url'],
                     'evidence_sha256': row['body_sha256'], 'fact_type': 'OBSERVED_TRANSITION',
                     'previous_evidence_sha256': old['body_sha256'],
                     'causality_proven': False, 'buy_signal': False}
            event['id'] = digest(json.dumps(event, sort_keys=True).encode())
            events.append(event)
    return events


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('--config', default='commercial_targets.json')
    cli.add_argument('--out', required=True)
    cli.add_argument('--history', default='history/snapshots')
    args = cli.parse_args()
    targets = json.loads(Path(args.config).read_text())['targets']
    monitoring = []
    for path in Path(args.history).glob('*/monitoring_targets.json'):
        monitoring.append(json.loads(path.read_text()))
    if monitoring:
        dynamic = max(monitoring, key=lambda r: r['observed_at'])['targets']
        if len(dynamic) > 4:
            raise ValueError('Research monitoring limit exceeded')
        targets += [t for t in dynamic if t['id'] not in {r['id'] for r in targets}]
    if not 1 <= len(targets) <= 10 or len({x['id'] for x in targets}) != len(targets):
        raise ValueError('Invalid targets')
    for target in targets:
        if not re.fullmatch(r'[a-z0-9_-]+', target['id']) or not target['url'].startswith('https://'):
            raise ValueError('Invalid target identity or URL')
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    report = {'schema': 'edge.commercial.snapshot.v1', 'observed_at': now(),
              'observations': [fetch(target, out) for target in targets]}
    count = sum(row['status'] == 'OK' for row in report['observations'])
    report['status'] = 'OK' if count == len(targets) else 'PARTIAL' if count else 'FAILED'
    history = []
    for path in Path(args.history).glob('*/report.json'):
        old = json.loads(path.read_text())
        if old.get('schema') == report['schema']:
            history.append(old)
    events = compare(report, history)
    comparisons = comparison_report(report, history)
    report['coverage'] = {
        'retail_offers_ok': sum(r['status'] == 'OK' and r['price_kind'] == 'ASKING_PRICE' for r in report['observations']),
        'indicative_prices_ok': sum(r['status'] == 'OK' and r['price_kind'] == 'AGGREGATED_INDICATIVE_LOW' for r in report['observations']),
        'failed_sources': len(targets) - count,
        'comparable_observations': sum(r['comparison_available'] for r in comparisons['observations']),
        'announcements_connected': False,
        'completed_sales_connected': False}
    (out / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
    (out / 'events.json').write_text(json.dumps({'schema': 'edge.commercial.events.v1', 'events': events}, indent=2))
    (out / 'comparisons.json').write_text(json.dumps(comparisons, indent=2))
    manifest = {p.name: digest(p.read_bytes()) for p in out.iterdir() if p.is_file()}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps({'status': report['status'], 'successful_offers': count, 'events': len(events)}))


if __name__ == '__main__':
    main()
