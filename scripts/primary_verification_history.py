"""Recheck reviewed official claims; missing or changed text remains unverified."""
import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from commercial_history import digest, now


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip = True
        if tag in ('h1', 'h2', 'h3', 'p', 'li'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = False
        if tag in ('h1', 'h2', 'h3', 'p', 'li'):
            self.parts.append('\n')

    def handle_data(self, text):
        if not self.skip:
            self.parts.append(text)


def text_content(html):
    parser = Text()
    parser.feed(html)
    return ' '.join(' '.join(parser.parts).split())


def extract(raw, source):
    html = raw.decode('utf-8')
    if source['extractor'] == 'heading_section':
        sections = re.split(r'(?=<h3\b)', html, flags=re.I)
        matching = [section for section in sections if re.search(r'<h3\b[^>]*>.*?' + re.escape(source['heading_reference']) + r'.*?</h3>', section, re.I | re.S)]
        if len(matching) != 1:
            raise ValueError('Expected exactly one reference-specific terms section')
        return text_content(matching[0])
    text = text_content(html)
    if source['extractor'] == 'product_intro':
        heading = source['heading_reference']
        # Price/status must be in the primary product area, not recommendation cards.
        match = re.search(r'<h1\b[^>]*>.*?' + re.escape(heading) + r'.*?</h1>', html, re.S | re.I)
        if not match:
            raise ValueError('Expected identified main product heading')
        return text_content(html[match.start():match.end() + 20000])
    return text


def check_source(raw, source):
    section = extract(raw, source)
    checks = [bool(re.search(pattern, section, re.I)) for pattern in source['patterns']]
    return {'status': 'VERIFIED_MATCH' if all(checks) else 'REVIEW_REQUIRED',
            'assertion_results': checks, 'section_sha256': digest(section.encode())}


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('--out', required=True)
    args = cli.parse_args()
    out = Path(args.out)
    plan = json.loads(Path('research/primary_reviews.json').read_text())
    report = {'schema': 'edge.primary.claim_rechecks.v1', 'observed_at': now(),
              'reviewed_at': plan['reviewed_at'], 'method': plan['mode'], 'sources': []}
    for source in plan['sources']:
        state = {'id': source['id'], 'source_url': source['url'], 'scope': source['scope'], 'status': 'FAILED'}
        try:
            with urlopen(Request(source['url'], headers={'User-Agent': 'EDGE-MarketResearch/1.0'}), timeout=25) as response:
                if response.status != 200 or urlsplit(response.url).hostname != urlsplit(source['url']).hostname:
                    raise ValueError('Unexpected official source response or redirect')
                raw = response.read(2000001)
            if len(raw) > 2000000 or not raw:
                raise ValueError('Invalid official response size')
            filename = 'primary_' + source['id'] + '.html'
            (out / filename).write_bytes(raw)
            state.update(raw_file=filename, body_sha256=digest(raw), **check_source(raw, source))
        except Exception as exc:
            state.update(error_type=type(exc).__name__, error=str(exc)[:200])
        report['sources'].append(state)
    states = {source['id']: source for source in report['sources']}
    report['reviews'] = []
    for review in plan['reviews']:
        required_ok = all(states[s]['status'] == 'VERIFIED_MATCH' for s in review['required_sources'])
        supported = [claim for claim in review['claims'] if states[claim['source_id']]['status'] == 'VERIFIED_MATCH']
        unsupported = [claim for claim in review['claims'] if states[claim['source_id']]['status'] != 'VERIFIED_MATCH']
        report['reviews'].append(dict(review, current_recheck_verified=required_ok,
            supported_claims=supported, unsupported_claims=unsupported,
            recheck_scope='FULL_REVIEWED_CLAIMS' if not unsupported else 'PARTIAL_REVIEWED_CLAIMS'))
    report['unresolved'] = plan['unresolved']
    (out / 'primary_verifications.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({'primary_sources': [(s['id'], s['status']) for s in report['sources']],
                      'currently_verified_reviews': sum(r['current_recheck_verified'] for r in report['reviews'])}))


if __name__ == '__main__':
    main()
