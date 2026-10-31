"""Source-linked observations only. No forecasts, actor motives or hypothetical returns."""
import argparse
import json
from pathlib import Path
from announcement_history import timestamp
from commercial_history import digest, now


def apply_primary_review(case, report):
    if not report:
        return
    review = next((r for r in report['reviews'] if r['candidate_id'] == case['candidate_id']), None)
    if not review:
        return
    if not review['current_recheck_verified']:
        case['primary_verification'] = {'status': 'RECHECK_FAILED_OR_CHANGED', 'observed_at': report['observed_at']}
        case['missing_data'].append('PRIMARY_CLAIMS_NOT_RECHECKED')
        return
    unsupported = review.get('unsupported_claims', [])
    case['primary_verification'] = {
        'status': 'REVIEWED_CLAIMS_PARTIALLY_RECHECKED' if unsupported else 'REVIEWED_CLAIMS_RECHECKED',
        'observed_at': report['observed_at'], 'reviewed_at': report['reviewed_at'],
        'full_local_terms_verified': case['candidate_id'] == 'lego_40889'}
    states = {s['id']: s for s in report['sources']}
    for claim in review.get('supported_claims', review['claims']):
        source = states[claim['source_id']]
        case['facts'].append({'type': 'VERIFIED_PRIMARY_CLAIM', 'claim': claim,
            'source_url': source['source_url'], 'scope': source['scope'],
            'evidence_sha256': source['body_sha256'], 'observed_at': report['observed_at']})
    case['missing_data'] = sorted(set(case['missing_data']) - set(review.get('remove_gaps', [])))
    if case['candidate_id'] == 'lego_40898':
        case['missing_data'].append('FRANCE_COMPLETE_GIFT_TERMS_UNCONFIRMED')
    if unsupported:
        case['missing_data'].append('SOME_PRIMARY_CLAIMS_NOT_RECHECKED')
        if any(c['kind'] == 'PUBLISHED_CATALOGUE_PRICE' for c in unsupported):
            case['missing_data'].append('FRENCH_CATALOGUE_PRICE_NOT_RECHECKED')
    if review.get('linked_opportunity_group'):
        case['linked_opportunity_group'] = review['linked_opportunity_group']
    dated = [c for c in review['claims'] if 'start_date' in c and 'end_date' in c]
    if dated:
        date = timestamp(case['assessed_at']).date().isoformat()
        start, end = min(c['start_date'] for c in dated), max(c['end_date'] for c in dated)
        case['event_phase'] = 'UPCOMING' if date < start else 'PAST_WINDOW' if date > end else 'SOURCE_DATE_WINDOW'


def assess(candidate, market, history, reaction_report, publications, assessed_at, primary=None, secondary=None, economics=None):
    cid = candidate['id']
    at = timestamp(assessed_at)
    facts = [{'type': 'PUBLICATION_REFERENCE', 'publication_id': e['publication_id'],
        'source_role': e['source_role'], 'source_url': e['source_url'],
        'source_published_at': e['published_at'], 'title': e['title'],
        'content_sha256': e['content_sha256']} for e in candidate['evidence']]
    quotes = [r for report in history + [market] for r in report['observations']
              if r['product_id'] == cid and r['status'] == 'OK' and r['price_kind'] == 'ASKING_PRICE'
              and timestamp(r['observed_at']) is not None and timestamp(r['observed_at']) <= at]
    latest = {}
    for row in sorted(quotes, key=lambda r: timestamp(r['observed_at'])):
        latest[(row['id'], row['url'], row['seller'], row['currency'])] = row
    for row in latest.values():
        age = (at - timestamp(row['observed_at'])).total_seconds() / 3600
        facts.append({'type': 'RETAIL_OBSERVATION', 'observation_id': row['id'], 'seller': row['seller'],
            'source_url': row['url'], 'price': row['price'], 'currency': row['currency'],
            'availability': row['availability'], 'observed_at': row['observed_at'],
            'age_hours': round(age, 2), 'fresh_within_24h': age <= 24, 'shipping_eur': row.get('shipping_eur'),
            'evidence_sha256': row['body_sha256'], 'completed_sale': False,
            'current_capture_status': next((r['status'] for r in market['observations']
                if r['id'] == row['id'] and r['url'] == row['url']), 'NOT_IN_CURRENT_CAPTURE')})
    ids = {e['publication_id'] for e in candidate['evidence']}
    measured = [w for m in reaction_report.get('measurements', [])
        if m['publication_id'] in ids and m.get('observation_id') in {r['id'] for r in quotes}
        for w in m.get('windows', []) if w['status'] == 'MEASURED']
    fresh = [f for f in facts if f['type'] == 'RETAIL_OBSERVATION' and f['fresh_within_24h']]
    gaps = ['REALIZED_TRANSACTION_PRICES_NOT_VERIFIED', 'LIQUIDITY_NOT_MEASURED', 'NET_MARGIN_NOT_MEASURED']
    if not fresh:
        gaps.append('NO_RECENT_RETAIL_QUOTE')
    if not measured:
        gaps.append('NO_MEASURED_EVENT_REACTION')
    if any(f['shipping_eur'] is None for f in fresh):
        gaps.append('DELIVERED_PRICE_UNKNOWN')
    case = {'id': 'assessment_' + cid, 'candidate_id': cid, 'sku': candidate['sku'],
        'assessed_at': assessed_at, 'data_policy': 'OBSERVED_DATA_ONLY_V1',
        'facts': facts, 'missing_data': gaps, 'measured_reaction_windows': measured,
        'financial_decision': 'NOT_COMPUTABLE_FROM_CURRENT_VERIFIED_DATA',
        'buy_signal': False, 'purchase_authorized': False}
    apply_primary_review(case, primary)
    if secondary and cid in ('lego_11388', 'lego_40889', 'lego_40898'):
        case['secondary_market_evidence'] = {
            'observed_at': secondary['observed_at'], 'status': secondary['status'],
            'listings': [r for r in secondary['listings'] if r['product_id'] == cid],
            'reviewed_historical_evidence': [r for r in secondary['reviewed_historical_evidence']['observations'] if r['sku'] == candidate['sku']],
            'one_time_baseline': [s for s in secondary.get('one_time_research_baseline', {}).get('sources', []) if s['sku'] == candidate['sku']],
            'one_time_baseline_refreshed_by_workflow': False,
            'france_delivered_offers_verified': 0, 'realized_transaction_prices_verified': 0}
    material = {'facts': [{k: v for k, v in f.items() if k not in ('observed_at', 'age_hours')} for f in facts],
                'missing_data': case['missing_data'], 'measured_reaction_windows': measured,
                'primary_status': case.get('primary_verification', {}).get('status'), 'event_phase': case.get('event_phase')}
    if case.get('secondary_market_evidence'):
        se = case['secondary_market_evidence']
        material['secondary'] = {k: v for k, v in se.items() if k != 'observed_at'}
    case['semantic_sha256'] = digest(json.dumps(material, sort_keys=True).encode())
    return case


def assign_revisions(cases, previous, observed):
    latest = {c['id']: c for report in sorted(previous, key=lambda r: r['observed_at']) for c in report['assessments']}
    changes = []
    for case in cases:
        old = latest.get(case['id'])
        changed = old is None or old['semantic_sha256'] != case['semantic_sha256']
        case['revision'] = 1 if old is None else old['revision'] + int(changed)
        case['first_assessed_at'] = old['first_assessed_at'] if old else observed
        changes.append({'assessment_id': case['id'], 'revision': case['revision'],
            'type': 'INITIAL_ASSESSMENT' if old is None else 'OBSERVATIONS_CHANGED' if changed else 'UNCHANGED',
            'previous_sha256': old['semantic_sha256'] if old else None, 'current_sha256': case['semantic_sha256']})
    return changes


def render(report):
    lines = ['# EDGE — Observations sourcées', '', 'Date du rapport : ' + report['observed_at'], '',
        'Uniquement des observations et des conditions publiées. Aucun scénario chiffré, projection ou valeur de revente supposée.', '',
        '| Référence | Prix affiché | Stock déclaré | Date du relevé | Source |', '|---|---:|---|---|---|']
    for case in report['assessments']:
        quotes = [f for f in case['facts'] if f['type'] == 'RETAIL_OBSERVATION']
        if not quotes:
            lines.append('| ' + case['sku'] + ' | Non relevé | Inconnu | — | Publications seules ou contrôles incomplets |')
        for f in quotes:
            stock = {'IN_STOCK': 'En stock', 'OUT_OF_STOCK': 'En rupture', 'UNKNOWN': 'Inconnu'}.get(f['availability'], f['availability'])
            label = ' ; ancien de plus de 24 h' if not f['fresh_within_24h'] else ''
            lines.append(f"| {case['sku']} | {f['price']} {f['currency']} | {stock} | {f['observed_at']}{label} | [{f['seller']}]({f['source_url']}) |")
    lines += ['', '## Conditions publiées vérifiées', '']
    for case in report['assessments']:
        for f in case['facts']:
            if f['type'] == 'VERIFIED_PRIMARY_CLAIM':
                claim = {k: v for k, v in f['claim'].items() if k != 'source_id'}
                lines.append('- Référence ' + case['sku'] + ' : ' + claim_text(claim) + ' [Source officielle](' + f['source_url'] + ').')
    lines += ['', '## Données non établies', '',
        'Prix réellement encaissés, volumes de transactions, liquidité et marges nettes : non établis par les données actuellement vérifiées.', '',
        '[Consulter les annonces secondaires et leur statut de collecte](economics_report.md).', '',
        '[Consulter séparément les estimations calculées et leur échantillon](probability_report.md).']
    return '\n'.join(lines) + '\n'


def claim_text(claim):
    kind = claim['kind']
    if kind in ('PUBLISHED_CATALOGUE_PRICE', 'PUBLISHED_RECOMMENDED_PRICE_EUR'):
        return 'prix publié ou annoncé de ' + claim['value'] + ' ' + claim['currency'] + ' ; commande exécutable non vérifiée.'
    if kind == 'ANNOUNCED_EARLY_ACCESS':
        return 'accès anticipé annoncé le ' + claim['date'] + ' pour les membres ' + claim['membership_required'] + '.'
    if kind == 'ANNOUNCED_GENERAL_RELEASE':
        return 'sortie générale annoncée le ' + claim['date'] + '.'
    if kind in ('ANNOUNCED_LINKED_GIFT', 'ANNOUNCED_CONDITIONAL_GIFT'):
        return 'cadeau 40898 annoncé avec le 11388 du ' + claim['start_date'] + ' au ' + claim['end_date'] + ', sous réserve de stock ; conditions françaises complètes non vérifiées.'
    if kind == 'GIFT_ELIGIBILITY':
        return 'cadeau en France dès ' + claim['minimum_spend_eur'] + ' € de marchandises LEGO, du ' + claim['start_date'] + ' au ' + claim['end_date'] + ', un par foyer, sous réserve de stock.'
    if kind == 'APPROXIMATE_PROMOTIONAL_VALUE':
        return 'valeur promotionnelle approximative publiée de ' + claim['value'] + ' ' + claim['currency'] + ', sans valeur de revente vérifiée.'
    return 'retour du cadeau requis avec les achats éligibles remboursés.'


def main():
    cli = argparse.ArgumentParser(); cli.add_argument('--out', required=True); cli.add_argument('--history', required=True)
    args = cli.parse_args(); out, root = Path(args.out), Path(args.history)
    markets, previous = [], []
    for folder in root.glob('*'):
        for name, collection in [('report.json', markets), ('assessments.json', previous)]:
            path = folder / name
            if path.is_file(): collection.append(json.loads(path.read_text()))
    discovery = json.loads((out / 'discovery.json').read_text())
    market = json.loads((out / 'report.json').read_text())
    reaction = json.loads((out / 'reactions.json').read_text())
    primary_path, secondary_path = out / 'primary_verifications.json', out / 'secondary_market.json'
    primary = json.loads(primary_path.read_text()) if primary_path.exists() else None
    secondary = json.loads(secondary_path.read_text()) if secondary_path.exists() else None
    observed = now()
    cases = [assess(c, market, markets, reaction, {}, observed, primary, secondary) for c in discovery['candidates']]
    cases.sort(key=lambda c: c['candidate_id'])
    report = {'schema': 'edge.mri.observed_dossiers.v2', 'observed_at': observed,
        'data_policy': 'OBSERVED_INPUTS_WITH_SEPARATE_LABELLED_ESTIMATES_V1', 'assessments': cases,
        'transitions': assign_revisions(cases, previous, observed), 'status': 'OK' if cases else 'EMPTY',
        'policy_migration': 'PREVIOUS_HYPOTHETICAL_REPORTS_REMAIN_HISTORICAL_ONLY',
        'financial_decisions_made': 0, 'purchase_authorized': False}
    market['coverage'].update(candidate_assessments=len(cases), assessment_status=report['status'], data_policy=report['data_policy'])
    probability_path = out / 'probabilities.json'
    if probability_path.exists():
        estimates = json.loads(probability_path.read_text())['estimates']
        market['coverage']['computed_probability_estimates'] = sum(e['estimated_probability'] is not None for e in estimates)
    market['coverage']['primary_review_matches'] = sum(c.get('primary_verification', {}).get('status') == 'REVIEWED_CLAIMS_RECHECKED' for c in cases)
    market['coverage']['primary_review_partial_matches'] = sum(c.get('primary_verification', {}).get('status') == 'REVIEWED_CLAIMS_PARTIALLY_RECHECKED' for c in cases)
    if primary:
        count = sum(s['status'] == 'VERIFIED_MATCH' for s in primary['sources'])
        status = 'OK' if count == len(primary['sources']) else 'PARTIAL' if count else 'FAILED'
        market['coverage']['primary_source_recheck_status'] = status
        if status != 'OK' and market['status'] == 'OK': market['status'] = 'PARTIAL'
    (out / 'report.json').write_text(json.dumps(market, indent=2, ensure_ascii=False))
    (out / 'assessments.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
    (out / 'assessment_report.md').write_text(render(report))
    manifest = {p.name: digest(p.read_bytes()) for p in out.iterdir() if p.is_file() and p.name != 'manifest.json'}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps({'observed_dossiers': len(cases), 'data_policy': report['data_policy']}))


if __name__ == '__main__': main()
