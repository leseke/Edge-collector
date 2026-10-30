"""Auditable research assessments; deterministic evidence rules, not return forecasts."""
import argparse
import datetime as dt
import json
import re
from pathlib import Path

from announcement_history import timestamp
from commercial_history import digest, now


def assess(candidate, market, history, reaction_report, publications, assessed_at):
    cid, sku = candidate['id'], candidate['sku']
    at = timestamp(assessed_at)
    facts = []
    texts = []
    for evidence in candidate['evidence']:
        pub = publications.get(evidence['publication_id'], {})
        texts.append(evidence['title'] + ' ' + pub.get('summary', ''))
        facts.append({'type': 'PUBLICATION_REFERENCE', 'publication_id': evidence['publication_id'],
            'source_role': evidence['source_role'], 'source_url': evidence['source_url'],
            'source_published_at': evidence['published_at'], 'title': evidence['title'],
            'mention_scope': 'TITLE_REFERENCE' if re.search(r'(?<!\d)' + re.escape(sku) + r'(?!\d)', evidence['title']) else 'SUMMARY_REFERENCE',
            'content_sha256': evidence['content_sha256'],
            'meaning': 'Cette publication mentionne la référence ; son existence ne prouve ni demande ni rareté.'})
    quote_history = [row for report in history + [market] for row in report['observations']
                     if row['product_id'] == cid and row['status'] == 'OK' and row['price_kind'] == 'ASKING_PRICE'
                     and timestamp(row['observed_at']) is not None and timestamp(row['observed_at']) <= at]
    by_source = {}
    for quote in sorted(quote_history, key=lambda r: timestamp(r['observed_at'])):
        by_source[(quote['id'], quote['url'], quote['seller'], quote['currency'])] = quote
    fresh = []
    for quote in by_source.values():
        age = (at - timestamp(quote['observed_at'])).total_seconds() / 3600
        fact = {'type': 'RETAIL_OBSERVATION', 'observation_id': quote['id'], 'seller': quote['seller'],
            'source_url': quote['url'], 'price': quote['price'], 'currency': quote['currency'],
            'availability': quote['availability'], 'observed_at': quote['observed_at'],
            'age_hours': round(age, 2), 'fresh_within_24h': age <= 24,
            'shipping_eur': quote.get('shipping_eur'), 'evidence_sha256': quote['body_sha256'],
            'current_capture_status': next((r['status'] for r in market['observations'] if r['id'] == quote['id'] and r['url'] == quote['url']), 'NOT_IN_CURRENT_CAPTURE'),
            'completed_sale': False}
        facts.append(fact)
        if age <= 24:
            fresh.append(fact)
    evidence_ids = {e['publication_id'] for e in candidate['evidence']}
    measurements = [m for m in reaction_report.get('measurements', []) if m['publication_id'] in evidence_ids
                    and m.get('observation_id') in {r['id'] for r in quote_history}]
    measured = [w for m in measurements for w in m.get('windows', []) if w['status'] == 'MEASURED']
    official = any(e['source_role'] == 'MANUFACTURER' for e in candidate['evidence'])
    announced = any(e['signal_context'] == 'ANNOUNCEMENT' for e in candidate['evidence'])
    promo = any(re.search(r'gift[ -]with[ -]purchase|\bGWP\b', text, re.I) for text in texts)
    media_count = len({e['source_id'] for e in candidate['evidence'] if e['source_role'] == 'SPECIALIST_MEDIA'})
    if promo:
        kind = 'PROMOTION_CONTEXT'
        thesis = "Un cadeau conditionné à l'achat pourrait modifier la valeur du panier et la demande pour la référence."
        counter = "Une diffusion large ou des conditions peu attractives pourraient limiter l'intérêt sur le marché secondaire."
        next_check = "Vérifier les conditions officielles, les pays, les dates et le seuil du cadeau ; suivre ensuite l'offre secondaire."
    elif announced:
        kind = 'ANNOUNCEMENT_CONTEXT'
        thesis = "L'annonce pourrait attirer une demande nouvelle avant que l'offre et les prix ne s'ajustent."
        counter = "Une offre abondante ou un intérêt déjà intégré aux prix pourrait supprimer l'asymétrie supposée."
        next_check = "Vérifier l'identité et le calendrier sur la source primaire, élargir les offres puis suivre la réaction."
    else:
        kind = 'REVIEW_OR_MENTION_CONTEXT'
        thesis = "Une publication pourrait susciter un regain d'attention pour une référence déjà commercialisée."
        counter = "La publication peut ne produire aucune demande supplémentaire ; le prix affiché peut rester inchangé."
        next_check = "Suivre les prix et disponibilités ; rechercher un catalyseur distinct et des indices de demande."
    priority = 'HIGH' if (official and announced) or promo else 'MEDIUM' if announced or fresh else 'LOW'
    action = 'INVESTIGATE_EVENT' if announced or promo else 'MONITOR_OBSERVATIONS' if fresh else 'VERIFY_PRODUCT_CONTEXT'
    gaps = ['REALIZED_SALES_NOT_CONNECTED', 'LIQUIDITY_UNKNOWN', 'SUPPLY_AND_REPRINTS_UNKNOWN',
            'RESALE_COSTS_AND_NET_MARGIN_UNKNOWN', 'CAUSALITY_UNPROVEN']
    if not fresh:
        gaps.append('NO_RECENT_RETAIL_QUOTE')
    if not official:
        gaps.append('NO_PRODUCT_SPECIFIC_MANUFACTURER_PUBLICATION_IN_COLLECTED_EVIDENCE')
    if not measured:
        gaps.append('NO_MEASURED_EVENT_REACTION')
    if any(q['shipping_eur'] is None for q in fresh):
        gaps.append('DELIVERED_PRICE_UNKNOWN')
    if promo:
        gaps.append('PROMOTION_TERMS_AND_REGION_NOT_VERIFIED')
    reasons = []
    if official:
        reasons.append('Une mention de la référence figure dans une publication du fabricant.')
    if announced:
        reasons.append("Le titre de certaines publications correspond à un contexte d'annonce ; les détails restent à vérifier.")
    if promo:
        reasons.append("Le texte collecté contient un contexte de cadeau avec achat ; ses conditions ne sont pas encore validées.")
    if fresh:
        reasons.append('Au moins un prix affiché récent permet de démarrer le suivi prospectif.')
    if not reasons:
        reasons.append('Les preuves disponibles justifient une vérification de contexte, sans catalyseur établi.')
    actors = [{'actor': 'FABRICANT', 'status': 'INCENTIVE_HYPOTHESIS',
               'hypothesis': "Créer de l'intérêt et convertir cet intérêt en achats pourrait être un objectif commercial.",
               'motive_verified': False}]
    if media_count:
        actors.append({'actor': 'MEDIAS_SPECIALISES', 'status': 'INCENTIVE_HYPOTHESIS',
            'hypothesis': "Informer et attirer une audience pourrait expliquer la couverture ; plusieurs articles ne prouvent pas plusieurs demandes indépendantes.",
            'motive_verified': False})
    if fresh:
        actors.append({'actor': 'VENDEUR', 'status': 'INCENTIVE_HYPOTHESIS',
            'hypothesis': "Vendre son stock en préservant sa marge pourrait guider son prix ; aucun motif individuel n'est établi.",
            'motive_verified': False})
    case = {'id': 'assessment_' + cid, 'candidate_id': cid, 'sku': sku, 'assessed_at': assessed_at,
        'method': 'DETERMINISTIC_EVIDENCE_RULES_V1', 'context': kind,
        'research_priority': priority, 'research_action': action, 'reasoning': reasons,
        'facts': facts,
        'weak_signals': [{'signal': 'MEDIA_COVERAGE', 'distinct_media_sources': media_count,
                         'demand_measurement': False, 'independence_verified': False}],
        'actor_hypotheses': actors,
        'early_hypothesis': {'status': 'UNTESTED_HYPOTHESIS', 'statement': thesis,
                             'counter_hypothesis': counter, 'probability': None},
        'scenarios': [
            {'id': 'ATTENTION_TRANSMISSION', 'type': 'CONDITIONAL_SCENARIO',
             'condition': "Si l'attention se traduit en demande et que l'offre ne suit pas, une tension pourrait apparaître.",
             'test': 'Comparer chronologiquement prix, stocks et ventes conclues quand ces dernières seront accessibles.',
             'invalidation': "Une offre durablement abondante et l'absence de réaction mesurée affaibliraient cette hypothèse."},
            {'id': 'NO_TRANSMISSION', 'type': 'CONDITIONAL_SCENARIO',
             'condition': "Si la couverture ne crée pas de demande additionnelle, la publication peut rester sans effet commercial.",
             'test': 'Observer les fenêtres J+1/J+3/J+7 sans transformer une donnée manquante en absence de réaction.',
             'invalidation': "Une réaction documentée et répétée justifierait de réexaminer ce scénario, sans prouver la causalité."}],
        'next_check': next_check, 'measured_reaction_windows': measured, 'missing_data': gaps,
        'investment_edge': 'UNPROVEN', 'financial_decision': 'UNASSESSED',
        'buy_signal': False, 'purchase_authorized': False}
    # Repeated timestamps alone must not look like a thesis revision.
    material = {'context': kind, 'priority': priority, 'action': action, 'gaps': gaps,
        'publications': sorted((f['publication_id'], f['content_sha256']) for f in facts if f['type'] == 'PUBLICATION_REFERENCE'),
        'quotes': sorted((f['observation_id'], f['source_url'], f['seller'], f['price'], f['currency'], f['availability'], f['fresh_within_24h'])
                         for f in facts if f['type'] == 'RETAIL_OBSERVATION'), 'measured_windows': measured}
    case['semantic_sha256'] = digest(json.dumps(material, sort_keys=True).encode())
    return case


def assign_revisions(cases, previous, observed):
    latest = {c['id']: c for report in sorted(previous, key=lambda r: r['observed_at']) for c in report['assessments']}
    transitions = []
    for case in cases:
        old = latest.get(case['id'])
        changed = old is None or old['semantic_sha256'] != case['semantic_sha256']
        case['revision'] = 1 if old is None else old['revision'] + int(changed)
        case['first_assessed_at'] = old['first_assessed_at'] if old else observed
        transitions.append({'assessment_id': case['id'], 'revision': case['revision'],
                            'type': 'INITIAL_ASSESSMENT' if old is None else 'ASSESSMENT_CHANGED' if changed else 'UNCHANGED',
                            'previous_sha256': old['semantic_sha256'] if old else None,
                            'current_sha256': case['semantic_sha256']})
    return transitions


def render(report):
    lines = ['# EDGE — Dossiers de recherche des candidats', '',
        'Évaluation par règles explicites. Les priorités orientent la recherche ; elles ne prédisent pas le rendement.', '',
        '| Référence | Priorité de recherche | Action | Révision |', '|---|---|---|---|']
    for case in report['assessments']:
        lines.append(f"| {case['sku']} | {case['research_priority']} | {case['research_action']} | {case['revision']} |")
    for case in report['assessments'][:3]:
        lines += ['', '## Référence ' + case['sku'], '', '**Pourquoi poursuivre la recherche**', ''] + ['- ' + reason for reason in case['reasoning']]
        lines += ['', '**Hypothèse précoce, non validée**', '', case['early_hypothesis']['statement'], '',
                  '**Contre-hypothèse**', '', case['early_hypothesis']['counter_hypothesis'], '',
                  '**Prochaine vérification**', '', case['next_check'], '', '**Preuves**', '']
        for fact in case['facts']:
            if fact['type'] == 'PUBLICATION_REFERENCE':
                title = fact['title'].replace('[', '(').replace(']', ')')
                lines.append('- [' + title + '](' + fact['source_url'] + ') — ' + fact['source_role'])
            else:
                lines.append('- Prix affiché : ' + fact['price'] + ' ' + fact['currency'] + ' ; stock déclaré : ' + fact['availability'] + ' ; relevé : ' + fact['observed_at'])
        lines += ['', '**Manques** : ' + ', '.join(case['missing_data']), '',
                  'Avantage économique : non démontré. Décision financière : non évaluée.']
    return '\n'.join(lines) + '\n'


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('--out', required=True)
    cli.add_argument('--history', required=True)
    args = cli.parse_args()
    out, root = Path(args.out), Path(args.history)
    markets, previous, publication_reports = [], [], []
    for folder in root.glob('*'):
        for name, collection in [('report.json', markets), ('assessments.json', previous), ('announcements.json', publication_reports)]:
            path = folder / name
            if path.is_file():
                collection.append(json.loads(path.read_text()))
    publication_reports.append(json.loads((out / 'announcements.json').read_text()))
    publications = {p['id']: p for report in sorted(publication_reports, key=lambda r: r['observed_at']) for p in report['publications']}
    discovery = json.loads((out / 'discovery.json').read_text())
    market = json.loads((out / 'report.json').read_text())
    reaction = json.loads((out / 'reactions.json').read_text())
    observed = now()
    cases = [assess(c, market, markets, reaction, publications, observed) for c in discovery['candidates']]
    order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    cases.sort(key=lambda c: (order[c['research_priority']], c['candidate_id']))
    transitions = assign_revisions(cases, previous, observed)
    report = {'schema': 'edge.mri.research_assessments.v1', 'observed_at': observed,
              'assessment_method': 'DETERMINISTIC_EVIDENCE_RULES_V1', 'assessments': cases,
              'transitions': transitions, 'status': 'OK' if cases else 'EMPTY',
              'financial_decisions_made': 0, 'purchase_authorized': False}
    market['coverage']['candidate_assessments'] = len(cases)
    market['coverage']['assessment_status'] = report['status']
    (out / 'report.json').write_text(json.dumps(market, indent=2, ensure_ascii=False))
    (out / 'assessments.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
    (out / 'assessment_report.md').write_text(render(report))
    manifest = {p.name: digest(p.read_bytes()) for p in out.iterdir() if p.is_file() and p.name != 'manifest.json'}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps({'assessed_candidates': len(cases), 'priorities': {p: sum(c['research_priority'] == p for c in cases) for p in order},
                      'financial_decisions': 0}))


if __name__ == '__main__':
    main()
