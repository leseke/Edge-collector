"""Bounded public listing asks and conditional bundle arithmetic, never sale-price estimates."""
import argparse
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from commercial_history import digest, now


class Cards(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cards = []
        self.card = None
        self.stack = []
        self.li_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get('class', '').split()
        if self.card is None and tag == 'li' and 's-card' in classes:
            self.card = dict(title=[], prices=[], text=[], seller_text=[], urls=[])
            self.li_depth = 0
            self.stack = []
        if self.card is None:
            return
        if tag == 'li':
            self.li_depth += 1
        if tag == 'a' and re.search(r'/itm/(\d{10,15})', attrs.get('href', '')):
            self.card['urls'].append(attrs['href'])
        if tag not in ('img', 'br', 'hr', 'input', 'meta', 'link', 'source', 'wbr', 'area', 'embed'):
            self.stack.append((tag, classes))

    def handle_endtag(self, tag):
        if self.card is None:
            return
        if tag == 'li':
            self.li_depth -= 1
            if self.li_depth == 0:
                self.cards.append(self.card)
                self.card = None
                return
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                self.stack = self.stack[:index]
                break

    def handle_data(self, text):
        if self.card is None:
            return
        classes = {c for _, cs in self.stack for c in cs}
        self.card['text'].append(text)
        if 's-card__title' in classes:
            self.card['title'].append(text)
        if 's-card__price' in classes:
            self.card['prices'].append(text)
        if 'su-card-container__attributes__secondary' in classes:
            self.card['seller_text'].append(text)


def parse_cards(raw, sku):
    parser = Cards()
    parser.feed(raw.decode('utf-8'))
    if not parser.cards:
        raise ValueError('No recognised listing cards; blocked or changed page is not an empty market')
    results = {}
    for card in parser.cards:
        title = ' '.join(' '.join(card['title']).split())
        if not re.search(r'\bLEGO\b', title, re.I) or not re.search(r'(?<!\d)' + sku + r'(?!\d)', title):
            continue
        urls = []
        for url in card['urls']:
            parts = urlsplit(url)
            if parts.scheme == 'https' and (parts.hostname or '').endswith('.ebay.ie'):
                urls.append(urlunsplit((parts.scheme, parts.netloc, parts.path, '', '')))
        ids = {re.search(r'/itm/(\d{10,15})', url).group(1) for url in urls}
        prices = re.findall(r'EUR\s*([\d,]+\.\d{2})', ' '.join(card['prices']))
        if len(ids) != 1 or len(set(prices)) != 1:
            continue
        listing_id = next(iter(ids))
        text = ' '.join(' '.join(card['text']).split())
        other_refs = set(re.findall(r'(?<![\w.,])([1-9]\d{4})(?![\w.,])', title)) - {sku}
        exclusions = []
        if other_refs or re.search(r'\bbundle\b|\blot of\b|\bcollection\b', title, re.I):
            exclusions.append('BUNDLE_OR_MULTIPLE_REFERENCES')
        if re.search(r'parts only|box only|instructions only|light kit|\bLED\b|without (?:box|minifig)|'
                     r'\bteca\b|\bvetrina\b|\bvitrine\b|plexiglass|acrilico|acrylic|showcase|display case|\bMOC\b|compatible|\blighting\b', title, re.I):
            exclusions.append('INCOMPLETE_OR_ACCESSORY')
        if re.search(r'\bminifig(?:ure)?s?\b', title, re.I) and not re.search(r'complete set|full set|with\s+\d+\s+minifig|\b5682\b', title, re.I):
            exclusions.append('MINIFIGURE_COMPONENT_NOT_COMPLETE_SET')
        if re.search(r'\belements?\b', title, re.I) and not re.search(r'complete set|full set|\b5682\b', title, re.I):
            exclusions.append('INDIVIDUAL_ELEMENT_NOT_COMPLETE_SET')
        presale = bool(re.search(r'pre[ -]?(?:sale|order)|presale|preventa|vorbestellung', title, re.I))
        shipping = re.search(r'\+EUR\s*([\d,]+\.\d{2})\s+(?:postage|shipping)', text, re.I)
        results[listing_id] = {'id': 'ebay_' + listing_id, 'listing_id': listing_id, 'product_id': 'lego_' + sku,
            'sku': sku, 'title': title, 'url': urls[0], 'asking_price_eur': prices[0].replace(',', ''),
            'evidence_class': 'SEARCH_CARD_ASK', 'sale_price_verified': False,
            'currency_basis': 'SEARCH_DISPLAY_EUR_NOT_VERIFIED_SETTLEMENT_CURRENCY',
            'completed_sale_verified': False, 'fulfilment': 'PRESALE_CLAIM' if presale else 'NOT_VERIFIED',
            'seller_declared_text': ' '.join(' '.join(card['seller_text']).split())[:350],
            'seller_reliability_verified': False,
            'displayed_shipping_eur': shipping.group(1).replace(',', '') if shipping else None,
            'shipping_quote_destination': 'UNCONFIRMED_SEARCH_CONTEXT',
            'france_delivery_verified': False, 'delivered_price_fr_eur': None,
            'individual_listing_verified': False, 'exclusions': exclusions, 'buy_signal': False}
    return list(results.values())


def euro(value):
    amount = Decimal(str(value))
    if not amount.is_finite() or amount < 0:
        raise ValueError('Invalid money input')
    return amount.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)


def required_net_gift(main_total, alternative_delivered, extra_costs):
    # Costs are explicit inputs. Unknown costs are never silently replaced by zero.
    if any(v is None for v in (main_total, alternative_delivered, extra_costs)):
        return None
    return str(max(Decimal('0'), euro(main_total) + euro(extra_costs) - euro(alternative_delivered)))


def scenarios():
    base = euro('499.99')
    rows = []
    for pct in (5, 10, 15):
        alternative = euro(base * (1 - Decimal(pct) / 100))
        rows.append({'alternative_discount_pct': pct, 'alternative_delivered_eur': str(alternative),
                     'required_gift_net_eur': required_net_gift(base, alternative, '0'),
                     'assumed_incremental_costs_eur': '0.00', 'type': 'HYPOTHETICAL_NOT_OBSERVED_OFFER',
                     'additional_costs_increase_threshold': True})
    return rows


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('--out', required=True)
    args = cli.parse_args()
    out = Path(args.out)
    report = {'schema': 'edge.secondary.listing_observations.v1', 'observed_at': now(), 'sources': [], 'listings': []}
    for sku in ('11388', '40889', '40898'):
        url = 'https://www.ebay.ie/sch/i.html?_nkw=LEGO+' + sku
        state = {'sku': sku, 'url': url, 'status': 'FAILED'}
        try:
            with urlopen(Request(url, headers={'User-Agent': 'EDGE-MarketResearch/1.0'}), timeout=25) as response:
                if response.status != 200 or urlsplit(response.url).hostname != 'www.ebay.ie':
                    raise ValueError('Unexpected search response or redirect')
                raw = response.read(2000001)
            if not raw or len(raw) > 2000000:
                raise ValueError('Invalid response size')
            filename = 'secondary_ebay_' + sku + '.html'
            (out / filename).write_bytes(raw)
            rows = parse_cards(raw, sku)[:20]
            for row in rows:
                row.update(observed_at=report['observed_at'], source_url=url, evidence_sha256=digest(raw))
            report['listings'].extend(rows)
            state.update(status='OK' if rows else 'NO_MATCH_IN_CAPTURED_CARDS', count=len(rows), raw_file=filename, sha256=digest(raw))
        except Exception as exc:
            state.update(error_type=type(exc).__name__, error=str(exc)[:200])
        report['sources'].append(state)
    reviewed = json.loads(Path('research/secondary_observations_2026-10-31.json').read_text())
    report['reviewed_historical_evidence'] = reviewed
    baseline_path = Path('research/secondary_seed_2026-10-31.json')
    if baseline_path.exists():
        report['one_time_research_baseline'] = json.loads(baseline_path.read_text())
    good = sum(s['status'] != 'FAILED' for s in report['sources'])
    report['status'] = 'OK' if good == 3 else 'PARTIAL' if good else 'FAILED'
    economics = {'schema': 'edge.bundle.conditional_economics.v1', 'observed_at': report['observed_at'],
        'opportunity_group': 'venice_launch_2026_11', 'main_announced_price_eur': '499.99',
        'main_price_basis': 'PREVIOUSLY_REVIEWED_MANUFACTURER_ANNOUNCEMENT_NOT_EXECUTABLE_QUOTE',
        'best_verified_france_delivered_alternative_eur': None, 'verified_gift_net_resale_eur': None,
        'incremental_costs_eur': None, 'measured_net_advantage_eur': None,
        'required_gift_net_actual_eur': required_net_gift('499.99', None, None),
        'gift_40889_included_in_bundle_revenue': False, 'gift_stacking_verified': False,
        'conditional_scenarios': scenarios(), 'evidence_status': 'INSUFFICIENT_FOR_MEASURED_NET_ADVANTAGE',
        'financial_decision': 'UNASSESSED', 'buy_signal': False, 'purchase_authorized': False}
    market = json.loads((out / 'report.json').read_text())
    market['coverage']['secondary_market_status'] = report['status']
    market['coverage']['secondary_listing_cards'] = len(report['listings'])
    market['coverage']['verified_net_bundle_advantage'] = False
    if report['status'] == 'FAILED' and market['status'] == 'OK':
        market['status'] = 'PARTIAL'
    (out / 'report.json').write_text(json.dumps(market, indent=2, ensure_ascii=False))
    (out / 'secondary_market.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
    (out / 'bundle_economics.json').write_text(json.dumps(economics, indent=2, ensure_ascii=False))
    (out / 'economics_report.md').write_text(render(report, economics))
    print(json.dumps({'secondary_status': report['status'], 'listing_cards': len(report['listings']), 'measured_net_advantage': None}))


def render(report, economics):
    lines = ['# EDGE — Offres secondaires et comparaison conditionnelle', '',
        'État de la collecte automatique : ' + report['status'] + '.', '',
        'Les cartes eBay ci-dessous indiquent des prix demandés. La vente individuelle, la livraison en France et le prix encaissé ne sont pas validés.', '',
        '| Référence | Annonce | Prix demandé EUR | Livraison FR vérifiée |', '|---|---|---:|---|']
    for row in report['listings']:
        title = row['title'].replace('|', '/').replace('[', '(').replace(']', ')')
        scope = ' — exclue de comparaison' if row['exclusions'] else ' — prévente annoncée' if row['fulfilment'] == 'PRESALE_CLAIM' else ''
        lines.append(f"| {row['sku']} | [{title}]({row['url']}){scope} | {row['asking_price_eur']} | Non |")
    baseline = report.get('one_time_research_baseline')
    if baseline:
        lines += ['', '## Relevé ponctuel distinct du suivi GitHub', '',
                  'Capture datée : ' + baseline['captured_at'] + '. Ce relevé provient de l’environnement de recherche ; il ne prouve pas que la collecte GitHub fonctionne et ne sera pas antidaté comme un relevé courant.', '',
                  '| Référence | Annonce indicative | Prix demandé EUR |', '|---|---|---:|']
        for source in baseline['sources']:
            for row in source['listings']:
                title = row['title'].replace('|', '/').replace('[', '(').replace(']', ')')
                lines.append(f"| {row['sku']} | [{title}]({row['url']}) | {row['asking_price_eur']} |")
    lines += ['', '## Observations manuelles datées du 31 octobre 2026', '']
    for row in report['reviewed_historical_evidence']['observations']:
        lines.append('- [' + row['label'] + '](' + row['url'] + ') : ' + row['interpretation'])
    lines += ['', '## Seuils conditionnels pour le panier Venise', '',
        'Base annoncée : 499,99 €. Les alternatives ci-dessous sont hypothétiques. Elles ne constituent pas des offres trouvées. Frais additionnels supposés nuls uniquement dans ce tableau ; tout frais réel augmente le seuil.', '',
        '| Remise hypothétique sur le set seul | Alternative livrée EUR | Recettes nettes du cadeau nécessaires EUR |', '|---|---:|---:|']
    for row in economics['conditional_scenarios']:
        lines.append(f"| {row['alternative_discount_pct']} % | {row['alternative_delivered_eur']} | {row['required_gift_net_eur']} |")
    lines += ['', "Le 40889 n'est pas ajouté aux recettes du panier : le cumul des cadeaux n'est pas confirmé.", '',
        'Avantage net observé : non calculable actuellement. Les frais, la livraison en France, une alternative exécutable et les recettes nettes du cadeau restent à établir.']
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    main()
