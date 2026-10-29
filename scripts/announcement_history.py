"""Observe publications and measure descriptive, product-specific reaction windows."""
import argparse
import datetime as dt
import email.utils
import json
import re
import xml.etree.ElementTree as ET
from decimal import Decimal
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from commercial_history import digest, now


def timestamp(value):
    try:
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        try:
            parsed = email.utils.parsedate_to_datetime(value)
        except (ValueError, TypeError, AttributeError):
            return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(dt.timezone.utc)


def clean(value):
    return ' '.join(unescape(re.sub('<[^>]*>', ' ', value or '')).split())


def canonical(url):
    parts = urlsplit(url)
    if parts.scheme != 'https' or not parts.hostname:
        raise ValueError('Expected HTTPS article URL')
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip('/'), '', ''))


class Newsroom(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self.item = None
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'c-card--article' in attrs.get('class', '').split():
            self.item = dict(url=urljoin('https://www.lego.com', attrs.get('href', '')),
                             title='', summary='', published_at=None)
        if self.item is not None:
            if tag == 'time':
                self.item['published_at'] = attrs.get('datetime')
            if tag == 'h2':
                self.in_title = True

    def handle_data(self, text):
        if self.item is not None:
            self.item['summary'] += ' ' + text
            if self.in_title:
                self.item['title'] += text

    def handle_endtag(self, tag):
        if tag == 'h2':
            self.in_title = False
        if tag == 'a' and self.item is not None:
            if self.item['title']:
                self.items.append(self.item)
            self.item = None


def parse(raw, source):
    if source['adapter'] == 'lego_newsroom':
        parser = Newsroom()
        parser.feed(raw.decode('utf-8'))
        items = parser.items
    else:
        if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
            raise ValueError('DTD not accepted')
        root = ET.fromstring(raw)
        if root.tag != 'rss' or root.find('channel') is None:
            raise ValueError('Expected RSS channel')
        items = [{'url': el.findtext('link'), 'title': el.findtext('title'),
                  'published_at': el.findtext('pubDate'),
                  'summary': el.findtext('description')} for el in root.findall('./channel/item')]
    if not items or len(items) > 300:
        raise ValueError('Empty or oversized publication list')
    result = {}
    for item in items:
        url = canonical(item['url'])
        if urlsplit(url).hostname.removeprefix('www.') != source['article_host']:
            continue
        title = clean(item['title'])[:500]
        if not title:
            continue
        published = timestamp(item['published_at'])
        row = {'id': digest((source['id'] + '\n' + url).encode()), 'source_id': source['id'],
               'source_role': source['role'], 'url': url, 'title': title,
               'summary': clean(item['summary'])[:6000],
               'published_at': published.isoformat() if published else None,
               'event_type': 'PUBLICATION', 'causality_proven': False, 'buy_signal': False}
        row['content_sha256'] = digest(json.dumps(row, sort_keys=True).encode())
        result[row['id']] = row
    if not result:
        raise ValueError('No validated publications')
    return list(result.values())


def register(items, previous, observed_at, source_initialized, targets):
    known = {}
    for report in previous:
        for row in report.get('publications', []):
            if row['id'] not in known or row['first_observed_at'] < known[row['id']]['first_observed_at']:
                known[row['id']] = row
    observed = timestamp(observed_at)
    for row in items:
        old = known.get(row['id'])
        row['first_observed_at'] = old['first_observed_at'] if old else observed_at
        row['observed_at'] = observed_at
        pub = timestamp(row['published_at'])
        row['detection_lag_hours'] = (observed - pub).total_seconds() / 3600 if pub else None
        row['future_dated'] = bool(pub and pub > observed)
        row['new_since_previous_capture'] = old is None and source_initialized
        row['imported_baseline'] = old['imported_baseline'] if old else not source_initialized
        row['product_ids'] = sorted({t['product_id'] for t in targets if t.get('adapter') != 'tcgdex'
                                    and re.search(r'(?<!\d)' + re.escape(t['sku']) + r'(?!\d)', row['title'] + ' ' + row['summary'])})
        row['product_link_method'] = 'EXACT_SKU_MENTION'
    return items


def reactions(publications, market_reports):
    output = []
    for event in publications:
        anchor = timestamp(event['published_at'])
        if not event['product_ids'] or not anchor or event['future_dated']:
            output.append({'publication_id': event['id'], 'status': 'NO_TRACKED_PRODUCT' if not event['product_ids'] else 'INVALID_PUBLICATION_TIME'})
            continue
        series = {}
        for report in market_reports:
            for row in report.get('observations', []):
                if row['status'] == 'OK' and row['product_id'] in event['product_ids'] and row['price_kind'] == 'ASKING_PRICE':
                    key = (row['id'], row['url'], row['seller'], row['product_id'], row['currency'])
                    series.setdefault(key, []).append(row)
        if not series:
            output.append({'publication_id': event['id'], 'status': 'NO_RETAIL_OBSERVATIONS'})
        for key, rows in series.items():
            before = [r for r in rows if anchor - dt.timedelta(hours=24) <= timestamp(r['observed_at']) <= anchor]
            result = {'publication_id': event['id'], 'observation_id': key[0],
                      'anchor': event['published_at'], 'anchor_kind': 'SOURCE_PUBLICATION_TIME',
                      'causality_proven': False, 'buy_signal': False, 'windows': []}
            baseline = max(before, key=lambda r: timestamp(r['observed_at'])) if before else None
            result['status'] = 'BASELINE_AVAILABLE' if baseline else 'NO_PRE_EVENT_BASELINE'
            for hours in (24, 72, 168):
                due = anchor + dt.timedelta(hours=hours)
                after = [r for r in rows if due <= timestamp(r['observed_at']) <= due + dt.timedelta(hours=6)]
                window = {'horizon_hours': hours, 'status': 'NO_PRE_EVENT_BASELINE' if not baseline else 'AWAITING_OBSERVATION'}
                if baseline and not after and max(timestamp(r['observed_at']) for r in rows) > due + dt.timedelta(hours=6):
                    window['status'] = 'MISSING_WINDOW_OBSERVATION'
                if baseline and after:
                    latest = min(after, key=lambda r: timestamp(r['observed_at']))
                    window.update(status='MEASURED', before_observed_at=baseline['observed_at'],
                                  after_observed_at=latest['observed_at'], before_price=baseline['price'],
                                  after_price=latest['price'], currency=key[4],
                                  asking_price_change_pct=str((Decimal(latest['price']) / Decimal(baseline['price']) - 1) * 100),
                                  before_availability=baseline['availability'], after_availability=latest['availability'],
                                  before_evidence_sha256=baseline['body_sha256'], after_evidence_sha256=latest['body_sha256'])
                result['windows'].append(window)
            output.append(result)
    return {'schema': 'edge.mri.reactions.v1', 'measurements': output,
            'metrics': 'ASKING_PRICES_AND_DECLARED_STOCK_ONLY', 'causality_proven': False}


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('--out', required=True)
    cli.add_argument('--history', required=True)
    args = cli.parse_args()
    out = Path(args.out)
    previous, markets = [], []
    for folder in Path(args.history).glob('*'):
        for filename, collection in [('announcements.json', previous), ('report.json', markets)]:
            path = folder / filename
            if path.is_file():
                collection.append(json.loads(path.read_text()))
    targets = json.loads(Path('commercial_targets.json').read_text())['targets']
    sources = json.loads(Path('announcement_sources.json').read_text())['sources']
    report = {'schema': 'edge.mri.publications.v1', 'observed_at': now(), 'sources': [], 'publications': []}
    for source in sources:
        state = {'id': source['id'], 'url': source['url'], 'status': 'FAILED'}
        try:
            with urlopen(Request(source['url'], headers={'User-Agent': 'EDGE-MarketResearch/1.0'}), timeout=25) as response:
                if response.status != 200 or urlsplit(response.url).hostname != urlsplit(source['url']).hostname:
                    raise ValueError('Unexpected response or redirect host')
                raw = response.read(2000001)
            if len(raw) > 2000000:
                raise ValueError('Oversized publication response')
            filename = 'announcements_' + source['id'] + '.raw'
            (out / filename).write_bytes(raw)
            initialized = any(s['id'] == source['id'] and s['status'] == 'OK' for old in previous for s in old['sources'])
            items = register(parse(raw, source), previous, report['observed_at'], initialized, targets)
            for item in items:
                item['evidence_sha256'] = digest(raw)
            report['publications'].extend(items)
            state.update(status='OK', count=len(items), raw_file=filename, sha256=digest(raw))
        except Exception as exc:
            state.update(error_type=type(exc).__name__, error=str(exc)[:200])
        report['sources'].append(state)
    count = sum(s['status'] == 'OK' for s in report['sources'])
    report['status'] = 'OK' if count == len(sources) else 'PARTIAL' if count else 'FAILED'
    # Retain previously seen articles even after they leave a rolling feed.
    all_events = {p['id']: p for old in previous for p in old['publications']}
    all_events.update({p['id']: p for p in report['publications']})
    current_market = json.loads((out / 'report.json').read_text())
    current_market['coverage']['announcements_connected'] = count > 0
    current_market['coverage']['announcement_sources_ok'] = count
    current_market['coverage']['announcement_status'] = report['status']
    if report['status'] != 'OK' and current_market['status'] == 'OK':
        current_market['status'] = 'PARTIAL'
    (out / 'report.json').write_text(json.dumps(current_market, indent=2, ensure_ascii=False))
    markets.append(current_market)
    (out / 'announcements.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
    (out / 'reactions.json').write_text(json.dumps(reactions(list(all_events.values()), markets), indent=2))
    manifest = {p.name: digest(p.read_bytes()) for p in out.iterdir() if p.is_file() and p.name != 'manifest.json'}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps({'announcement_status': report['status'], 'publications': len(report['publications']),
                      'new_publications': sum(p['new_since_previous_capture'] for p in report['publications'])}))


if __name__ == '__main__':
    main()
