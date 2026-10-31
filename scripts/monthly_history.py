"""Import a hash-pinned published monthly dataset, keeping its native scope."""
import argparse
import gzip
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from commercial_history import now

REVISION = '2b0f769c2076ab89f1ece8a1c096c3422adb497f'
BLOB = '782f61e0f7d4e20d9cf0ace2ba8c2e404cd98e00'
SHA256 = '3fb7471eb63154eb3c6ec2bee1e369f03b6622f127be187b9962f07cdf9f0861'
SOURCE = f'https://raw.githubusercontent.com/BartekPodgorski/Lego_Predict/{REVISION}/lego_data_price_history.xlsx'
ARTICLE = 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10828600/'
IMPORT_ID = 'lego_predict_2018_2023_monthly_v1'
N = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def verify(raw):
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    if hashlib.sha256(raw).hexdigest() != SHA256 or blob != BLOB:
        raise ValueError('Published artifact checksum mismatch')


def xlsx_rows(path):
    with zipfile.ZipFile(path) as book:
        strings = []
        if 'xl/sharedStrings.xml' in book.namelist():
            strings = [''.join(si.itertext()) for si in ET.fromstring(book.read('xl/sharedStrings.xml'))]
        with book.open('xl/worksheets/sheet1.xml') as sheet:
            for _, row in ET.iterparse(sheet, events=['end']):
                if row.tag != N + 'row': continue
                values = {}
                for cell in row:
                    column = re.sub(r'\d', '', cell.get('r', ''))
                    if cell.find(N + 'f') is not None:
                        raise ValueError('Formulas are not accepted as historical evidence')
                    value = ''.join(cell.find(N + 'is').itertext()) if cell.get('t') == 'inlineStr' else cell.findtext(N + 'v', '')
                    values[column] = strings[int(value)] if cell.get('t') == 's' else value
                yield int(row.get('r')), [values.get(c, '') for c in ('A', 'B', 'C')]
                row.clear()


def normalize(rows):
    series, seen = {}, {}
    counts = {'source_rows': 0, 'positive_prices': 0, 'zero_coded_missing_prices': 0, 'duplicate_rows': 0, 'raw_zero_coded_rows': 0}
    header = next(rows, None)
    if header is None or header[1] != ['Date', 'Price', 'url']:
        raise ValueError('Unexpected published workbook schema')
    for number, values in rows:
        month, price_text, url = values
        if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', month) or not '2018-06' <= month <= '2023-06':
            raise ValueError('Invalid historical month at row ' + str(number))
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.netloc != 'promoklocki.pl' or not re.fullmatch(r'/lego-[a-z0-9-]+-h\d+', parsed.path):
            raise ValueError('Unexpected historical series URL at row ' + str(number))
        try: price = Decimal(price_text)
        except InvalidOperation: raise ValueError('Invalid price at row ' + str(number))
        if not price.is_finite() or price < 0: raise ValueError('Invalid price at row ' + str(number))
        counts['source_rows'] += 1
        counts['raw_zero_coded_rows'] += price == 0
        key = (url, month)
        if key in seen:
            if seen[key] != price: raise ValueError('Conflicting prices for one URL/month')
            counts['duplicate_rows'] += 1
            continue
        seen[key] = price
        counts['positive_prices' if price > 0 else 'zero_coded_missing_prices'] += 1
        item = series.setdefault(url, {'id': hashlib.sha256(url.encode()).hexdigest(), 'source_url': url, 'points': []})
        item['points'].append({'month': month, 'price_pln': str(price) if price > 0 else None,
            'source_price_text': price_text, 'source_row': number,
            'status': 'OBSERVED_MONTHLY_MAXIMUM' if price > 0 else 'SOURCE_ZERO_CODED_UNAVAILABLE_PRICE_MISSING'})
    result = sorted(series.values(), key=lambda x: x['source_url'])
    for s in result: s['points'].sort(key=lambda p: p['month'])
    return result, counts


def month_index(value):
    year, month = map(int, value.split('-')); return year * 12 + month


def summarize(series, counts):
    windows = 0
    for s in series:
        p = s['points']
        for i in range(3, len(p)):
            group = p[i-3:i+1]
            if (all(x['price_pln'] is not None for x in group)
                    and month_index(group[-1]['month']) - month_index(group[0]['month']) == 3):
                windows += 1
    example = next((s for s in series if s['source_url'] == 'https://promoklocki.pl/lego-icons-10312-klub-jazzowy-h22044'), None)
    return {'schema': 'edge.mri.imported_monthly_history.v1', 'status': 'IMPORTED_NATIVE_SCOPE',
        'dataset_id': IMPORT_ID, 'generated_at': now(), 'source_url': SOURCE, 'article_url': ARTICLE,
        'source_revision': REVISION, 'source_git_blob_sha1': BLOB, 'source_sha256': SHA256,
        'attribution': 'W. Oczkos, B. Podgorski, W. Szczepanska, T. Boinski; Data in Brief 52 (2024), 110056; dataset DOI 10.34808/s25h-sx91',
        'market': 'PL', 'currency': 'PLN', 'aggregation': 'MONTHLY_MAXIMUM_PER_SOURCE_METHOD_AND_CODE',
        'granularity': 'MONTH', 'source_period_start': '2018-06', 'source_period_end': '2023-06',
        'coverage': dict(counts, series_count=len(series), unique_series_months=sum(len(s['points']) for s in series), complete_four_consecutive_month_windows=windows),
        'source_identity': 'SOURCE_URL; NO_OFFICIAL_VARIANT_JOIN_VERIFIED',
        'point_in_time_availability_verified': False, 'completed_sales_verified': False,
        'linked_to_daily_stock_estimator': False, 'predictive_performance': None, 'buy_signal': False,
        'limitations': ['Maxima mensuels ; prix moyens et offres actuellement exécutables non établis.',
            'Zéros source conservés comme prix manquants ; aucune variation depuis un prix nul ni rupture datée déduite.',
            'Délai de publication et révisions historiques inconnus ; validation en conditions historiques réelles non établie.',
            'Pays, devise et agrégation conservés : Pologne, PLN, maximum mensuel.',
            'Fenêtres superposées et séries dépendantes ; leur nombre ne représente pas des essais indépendants.'],
        'example_series': example}


def render(report):
    c = report['coverage']
    lines = ['# EDGE — Historique mensuel importé', '',
        f"Lignes source : {c['source_rows']}. Doublons identiques écartés : {c['duplicate_rows']}. Observations URL/mois uniques : {c['unique_series_months']}. Séries distinctes par URL : {c['series_count']}. Prix positifs uniques : {c['positive_prices']}. Zéros uniques conservés comme prix manquants : {c['zero_coded_missing_prices']}.", '',
        'Périmètre : Pologne, PLN, juin 2018 à juin 2023. Maximum mensuel selon la méthode et le code source des auteurs.', '',
        f"Fenêtres de quatre mois consécutifs avec prix renseignés : {c['complete_four_consecutive_month_windows']}. Ces fenêtres se recouvrent ; elles ne sont pas des essais indépendants.", '',
        '[Article et méthode](' + ARTICLE + '). Empreintes SHA-256 et Git vérifiées ; fichier original et séries normalisées conservés dans imports/' + IMPORT_ID + '/.', '']
    e = report.get('example_series')
    if e:
        lines += ['## Exemple conservé : URL source LEGO Icons 10312', '', '[Série source](' + e['source_url'] + ')', '', '| Mois | Maximum mensuel source (PLN) |', '|---|---:|']
        for p in e['points']: lines.append('| ' + p['month'] + ' | ' + (p['price_pln'] or 'Manquant') + ' |')
    lines += ['', '## Limites de mesure', ''] + ['- ' + x for x in report['limitations']]
    lines += ['', 'Les précédents mensuels sont disponibles pour une analyse de trajectoires distincte. Aucune probabilité quotidienne de stock, performance prédictive ni instruction d’achat n’est produite par cet import.']
    return '\n'.join(lines) + '\n'


def main():
    cli = argparse.ArgumentParser(); cli.add_argument('--out', required=True); cli.add_argument('--cache', required=True)
    args = cli.parse_args(); out, cache = Path(args.out), Path(args.cache) / IMPORT_ID
    out.mkdir(parents=True, exist_ok=True); cache.mkdir(parents=True, exist_ok=True)
    original = cache / 'source.xlsx'
    try:
        if not original.exists():
            request = Request(SOURCE, headers={'User-Agent': 'EDGE-MarketResearch/1.0'})
            with urlopen(request, timeout=40) as response: raw = response.read(4000001)
            verify(raw); original.write_bytes(raw)
            (cache / 'acquisition.json').write_text(json.dumps({'retrieved_at': now(), 'source_url': SOURCE, 'sha256': SHA256}, indent=2))
        verify(original.read_bytes())
        series, counts = normalize(iter(xlsx_rows(original)))
        report = summarize(series, counts)
        normalized = json.dumps({'dataset_id': IMPORT_ID, 'series': series}, ensure_ascii=False, sort_keys=True).encode()
        normalized_path = cache / 'monthly_series.json.gz'
        normalized_path.write_bytes(gzip.compress(normalized, mtime=0))
        report['normalized_sha256'] = hashlib.sha256(normalized_path.read_bytes()).hexdigest()
        (cache / 'provenance.json').write_text(json.dumps({k: v for k,v in report.items() if k not in ('generated_at','example_series')}, indent=2, ensure_ascii=False))
        (out / 'monthly_history_report.md').write_text(render(report))
    except Exception as exc:
        report = {'schema': 'edge.mri.imported_monthly_history.v1', 'status': 'FAILED', 'generated_at': now(),
                  'source_url': SOURCE, 'error': str(exc)[:300], 'buy_signal': False}
        (out / 'monthly_history_report.md').write_text('# EDGE — Import mensuel indisponible\n\n' + report['error'] + '\n')
    (out / 'monthly_history.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({k:v for k,v in report.items() if k in ('status','coverage','error')}))


if __name__ == '__main__': main()
