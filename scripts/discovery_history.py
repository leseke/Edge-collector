"""Publication-led LEGO candidates and bounded, identity-checked retail research."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

from commercial_history import compare, comparison_report, digest, fetch, now, parse_offer
from announcement_history import reactions, timestamp


def references(publication):
    title, summary = publication['title'], publication.get('summary', '')
    # Avoid historical daily features and list statistics masquerading as launch signals.
    if re.search(r'random (set|figure)|vintage set|top news|what.s hot|recent reviews', title, re.I):
        return []
    found = set(re.findall(r'(?<![\w.,])([1-9]\d{4})(?![\w.,])', title))
    # Summary references must have a product context; bare view counts are excluded.
    patterns = [r'\(([1-9]\d{4})\)\s*set\b',
                r'\b(?:set|LEGO|model)\s+([1-9]\d{4})\b',
                r'(?:^|[.!?]\s+)([1-9]\d{4})\s+[A-Z][A-Za-z]+',
                r'\b([1-9]\d{4})\s+[A-Z][A-Za-z]+\s+[A-Z][A-Za-z]+']
    for pattern in patterns:
        found.update(re.findall(pattern, summary))
    return sorted(found)


def build_candidates(publications, previous, observed):
    candidates = {c['id']: dict(c) for report in sorted(previous, key=lambda r: r['observed_at'])
                  for c in report['candidates']}
    for publication in publications:
        title = publication['title']
        signal = ('ANNOUNCEMENT' if re.search(r'announc|reveal|launch|new.+set', title, re.I)
                  else 'PROMOTION' if re.search(r'gift.with.purchase|GWP|available now|offer', title, re.I)
                  else 'REVIEW' if re.search(r'review|quick look', title, re.I) else 'MENTION')
        for sku in references(publication):
            cid = 'lego_' + sku
            candidate = candidates.setdefault(cid, {'id': cid, 'sku': sku, 'status': 'DISCOVERED',
                'first_observed_at': observed, 'evidence': [], 'last_probe_at': None,
                'buy_signal': False, 'purchase_authorized': False})
            candidate['last_seen_at'] = max(candidate.get('last_seen_at', ''), publication['observed_at'])
            evidence = {'publication_id': publication['id'], 'source_id': publication['source_id'],
                        'source_role': publication['source_role'], 'source_url': publication['url'],
                        'published_at': publication['published_at'], 'signal_context': signal,
                        'title': title, 'content_sha256': publication['content_sha256']}
            candidate['evidence'] = [e for e in candidate['evidence'] if e['publication_id'] != publication['id']] + [evidence]
            candidate['identity_status'] = 'EXPLICIT_REFERENCE_NOT_YET_CATALOGUE_VERIFIED'
    for candidate in candidates.values():
        evidence = candidate['evidence']
        candidate['latest_publication_at'] = max((e['published_at'] or '' for e in evidence), default='')
        candidate['priority_score'] = (30 * any(e['signal_context'] == 'ANNOUNCEMENT' for e in evidence)
                                      + 20 * any(e['source_role'] == 'MANUFACTURER' for e in evidence)
                                      + 5 * any(e['signal_context'] == 'REVIEW' for e in evidence)
                                      + min(10, len({e['source_id'] for e in evidence}) * 2))
    return sorted(candidates.values(), key=lambda c: (-c['priority_score'], c['id']))


def select_probes(candidates):
    # Oldest probe first ensures sustained rotation; one review gives a current-market control.
    ordered = sorted(candidates, key=lambda c: (c.get('last_probe_at') or '', -c['priority_score'],
                     -(timestamp(c['latest_publication_at']).timestamp() if timestamp(c['latest_publication_at']) else 0), c['id']))
    picked = ordered[:2]
    review = next((c for c in ordered if c not in picked and any(e['signal_context'] == 'REVIEW' for e in c['evidence'])), None)
    if review:
        picked.append(review)
    elif len(ordered) > 2:
        picked.append(ordered[2])
    return picked


def probe(candidate, out):
    sku = candidate['sku']
    query_url = 'https://www.ldlc.com/recherche/' + sku + '/'
    result = {'candidate_id': candidate['id'], 'observed_at': now(), 'search_url': query_url,
              'status': 'FAILED', 'coverage': 'BOUNDED_SEARCH_NOT_EXHAUSTIVE', 'attempts': []}
    try:
        with urlopen(Request(query_url, headers={'User-Agent': 'EDGE-MarketResearch/1.0'}), timeout=18) as response:
            final_url = response.url
            if response.status != 200 or urlsplit(final_url).hostname != 'www.ldlc.com':
                raise ValueError('Unexpected search response or host')
            raw = response.read(2000001)
        if not raw or len(raw) > 2000000:
            raise ValueError('Invalid search response size')
        (out / ('search_ldlc_' + sku + '.html')).write_bytes(raw)
        result['search_sha256'] = digest(raw)
        # A direct product redirect is common for an exact reference query.
        if re.fullmatch(r'/fiche/PB\d+\.html', urlsplit(final_url).path):
            links = [final_url]
        else:
            text = raw.decode('utf-8')
            if 'id="searchPage"' not in text:
                raise ValueError('Unrecognised search document')
            links = list(dict.fromkeys(urljoin('https://www.ldlc.com', link) for link in
                re.findall(r'href=["\']((?:https://www\.ldlc\.com)?/fiche/PB\d+\.html)', text)))[:2]
        for index, url in enumerate(links):
            target = {'id': 'ldlc_discovered_' + sku, 'sku': sku, 'product_id': candidate['id'],
                      'seller': 'LDLC', 'expected_offer_seller': 'LDLC',
                      'source_qualification': 'ESTABLISHED_RETAILER', 'url': url}
            # Keep each attempted page; do not overwrite a failed identity's evidence.
            attempt_target = dict(target, id=target['id'] + '_probe_' + str(index))
            row = fetch(attempt_target, out)
            result['attempts'].append(row)
            if row['status'] == 'OK':
                row['id'] = target['id']
                result.update(status='OFFER_VERIFIED', target=target, observation=row)
                return result
        result['status'] = 'NO_VERIFIED_OFFER'
    except Exception as exc:
        result.update(error_type=type(exc).__name__, error=str(exc)[:200])
    return result


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('--out', required=True)
    cli.add_argument('--history', required=True)
    args = cli.parse_args()
    out, root = Path(args.out), Path(args.history)
    previous, markets, publication_reports, monitoring = [], [], [], []
    for folder in root.glob('*'):
        for filename, collection in [('discovery.json', previous), ('report.json', markets),
                                     ('announcements.json', publication_reports), ('monitoring_targets.json', monitoring)]:
            path = folder / filename
            if path.is_file():
                collection.append(json.loads(path.read_text()))
    current = json.loads((out / 'announcements.json').read_text())
    publication_reports.append(current)
    # Use the latest version of each publication, including those no longer in feeds.
    publications = {p['id']: p for report in sorted(publication_reports, key=lambda r: r['observed_at']) for p in report['publications']}
    observed = now()
    candidates = build_candidates(list(publications.values()), previous, observed)
    results = []
    targets = max(monitoring, key=lambda r: r['observed_at'])['targets'] if monitoring else []
    targets = [dict(t) for t in targets]
    for candidate in select_probes(candidates):
        result = probe(candidate, out)
        candidate['last_probe_at'] = observed
        candidate['last_probe_status'] = result['status']
        results.append(result)
        if result['status'] == 'OFFER_VERIFIED':
            candidate['status'] = 'RETAIL_IDENTITY_VERIFIED'
            candidate['identity_status'] = 'RETAIL_REFERENCE_AND_SELLER_MATCHED'
            target = result['target']
            if any(t['id'] == target['id'] for t in targets):
                targets = [target if t['id'] == target['id'] else t for t in targets]
            elif len(targets) < 4:
                targets.append(target)
            candidate['research_monitoring'] = any(t['id'] == target['id'] for t in targets)
    market = json.loads((out / 'report.json').read_text())
    for result in results:
        if result['status'] == 'OFFER_VERIFIED' and not any(r['id'] == result['observation']['id'] for r in market['observations']):
            market['observations'].append(result['observation'])
    market['coverage']['discovery_candidates'] = len(candidates)
    market['coverage']['discovery_probes'] = len(results)
    market['coverage']['research_monitoring_targets'] = len(targets)
    market['coverage']['retail_offers_ok'] = sum(r['status'] == 'OK' and r['price_kind'] == 'ASKING_PRICE' for r in market['observations'])
    successes = sum(r['status'] == 'OK' for r in market['observations'])
    market['coverage']['failed_sources'] = len(market['observations']) - successes
    market['status'] = 'FAILED' if not successes else 'PARTIAL' if successes < len(market['observations']) else 'OK'
    if current['status'] != 'OK' and market['status'] == 'OK':
        market['status'] = 'PARTIAL'
    comparisons = comparison_report(market, markets)
    market['coverage']['comparable_observations'] = sum(r['comparison_available'] for r in comparisons['observations'])
    market['coverage']['discovery_status'] = 'EMPTY' if not candidates else 'PARTIAL' if any(r['status'] == 'FAILED' for r in results) else 'OK'
    # Product links remain explicit SKU mentions, including the newly discovered references.
    for event in publications.values():
        ids = ['lego_' + sku for sku in references(event)]
        event['product_ids'] = sorted(set(event['product_ids'] + ids))
    current['publications'] = [publications[p['id']] for p in current['publications']]
    report = {'schema': 'edge.discovery.publication_candidates.v1', 'observed_at': observed,
              'candidates': candidates, 'probes': results, 'status': market['coverage']['discovery_status'],
              'manual_financial_promotion_required': True, 'purchase_authorized': False}
    files = {'discovery.json': report, 'monitoring_targets.json': {'observed_at': observed, 'targets': targets,
              'scope': 'RESEARCH_ONLY_NOT_FINANCIAL_WATCHLIST'}, 'report.json': market,
              'comparisons.json': comparisons, 'announcements.json': current,
              'events.json': {'schema': 'edge.commercial.events.v1', 'events': compare(market, markets)},
              'reactions.json': reactions(list(publications.values()), markets + [market])}
    for name, content in files.items():
        (out / name).write_text(json.dumps(content, indent=2, ensure_ascii=False))
    manifest = {p.name: digest(p.read_bytes()) for p in out.iterdir() if p.is_file() and p.name != 'manifest.json'}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps({'candidates': len(candidates), 'probes': [(r['candidate_id'], r['status']) for r in results],
                      'monitoring': len(targets)}))


if __name__ == '__main__':
    main()
