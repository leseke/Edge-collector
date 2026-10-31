"""Auditable research assessments; deterministic evidence rules, not return forecasts."""
import argparse
import datetime as dt
import json
import re
from pathlib import Path

from announcement_history import timestamp
from commercial_history import digest, now


def assess(candidate, market, history, reaction_report, publications, assessed_at, primary=None, secondary=None, economics=None):
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
    apply_primary_review(case, primary)
    if secondary and cid in ('lego_11388', 'lego_40889', 'lego_40898'):
        listings = [row for row in secondary['listings'] if row['product_id'] == cid]
        reviewed = [row for row in secondary['reviewed_historical_evidence']['observations'] if row['sku'] == sku]
        case['secondary_market_evidence'] = {'observed_at': secondary['observed_at'], 'listings': listings,
            'reviewed_historical_evidence': reviewed, 'france_delivered_offers_verified': 0,
            'realized_transaction_prices_verified': 0, 'status': secondary['status']}
        if economics and case.get('linked_opportunity_group') == economics['opportunity_group']:
            case['conditional_bundle_economics'] = economics
    # Repeated timestamps alone must not look like a thesis revision.
    material = {'context': case['context'], 'priority': case['research_priority'], 'action': case['research_action'], 'gaps': case['missing_data'],
        'publications': sorted((f['publication_id'], f['content_sha256']) for f in facts if f['type'] == 'PUBLICATION_REFERENCE'),
        'quotes': sorted((f['observation_id'], f['source_url'], f['seller'], f['price'], f['currency'], f['availability'], f['fresh_within_24h'])
                         for f in facts if f['type'] == 'RETAIL_OBSERVATION'), 'measured_windows': measured}
    if 'primary_verification' in case:
        material.update(primary_claims=[f['claim'] for f in facts if f['type'] == 'VERIFIED_PRIMARY_CLAIM'],
                        primary_status=case['primary_verification']['status'], event_phase=case.get('event_phase'),
                        early_hypothesis=case['early_hypothesis'], scenarios=case['scenarios'])
    if 'secondary_market_evidence' in case:
        material['secondary_cards'] = sorted((r['id'], r['asking_price_eur'], r['fulfilment'], tuple(r['exclusions']))
                                            for r in case['secondary_market_evidence']['listings'])
        material['secondary_status'] = case['secondary_market_evidence']['status']
        material['reviewed_secondary_evidence'] = case['secondary_market_evidence']['reviewed_historical_evidence']
    case['semantic_sha256'] = digest(json.dumps(material, sort_keys=True).encode())
    return case


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
    source_states = {s['id']: s for s in report['sources']}
    unsupported = review.get('unsupported_claims', [])
    case['primary_verification'] = {'status': 'REVIEWED_CLAIMS_PARTIALLY_RECHECKED' if unsupported else 'REVIEWED_CLAIMS_RECHECKED', 'observed_at': report['observed_at'],
                                  'reviewed_at': report['reviewed_at'], 'full_local_terms_verified': case['candidate_id'] == 'lego_40889'}
    for claim in review.get('supported_claims', review['claims']):
        source = source_states[claim['source_id']]
        case['facts'].append({'type': 'VERIFIED_PRIMARY_CLAIM', 'claim': claim, 'source_url': source['source_url'],
            'scope': source['scope'], 'evidence_sha256': source['body_sha256'], 'observed_at': report['observed_at']})
    for field in ('context', 'research_priority', 'research_action', 'reasoning', 'next_check'):
        case[field] = review[field]
    case['early_hypothesis']['statement'] = review['thesis']
    case['early_hypothesis']['counter_hypothesis'] = review['counter']
    case['missing_data'] = sorted(set(case['missing_data']) - set(review['remove_gaps']) | set(review['add_gaps']))
    if unsupported:
        case['missing_data'].append('SOME_PRIMARY_CLAIMS_NOT_RECHECKED')
        if any(c['kind'] == 'PUBLISHED_CATALOGUE_PRICE' for c in unsupported):
            case['missing_data'].append('FRENCH_CATALOGUE_PRICE_NOT_RECHECKED')
    if review.get('linked_opportunity_group'):
        case['linked_opportunity_group'] = review['linked_opportunity_group']
        case['bundle_economics'] = {'model': 'MAIN_SET_AND_GIFT_NOT_INDEPENDENT_PROFITS',
            'main_set_catalogue_price_eur': '499.99', 'gift_net_resale_proceeds_eur': None,
            'alternative_delivered_main_set_price_eur': None, 'net_advantage_eur': None,
            'price_basis': 'MANUFACTURER_ANNOUNCED_PRICE_NOT_EXECUTABLE_QUOTE',
            'gift_stacking_verified': False, 'nominal_gift_values_used_as_revenue': False}
    dated = [claim for claim in review['claims'] if 'start_date' in claim and 'end_date' in claim]
    if dated:
        start, end = min(c['start_date'] for c in dated), max(c['end_date'] for c in dated)
        date = timestamp(case['assessed_at']).date().isoformat()
        case['event_phase'] = 'UPCOMING' if date < start else 'PAST_WINDOW' if date > end else 'SOURCE_DATE_WINDOW'
        if date > end:
            case['research_priority'] = 'MEDIUM'
            case['research_action'] = 'CHECK_POST_EVENT_MARKET'
            case['next_check'] = "La fenêtre annoncée est passée : vérifier une éventuelle prolongation et l'offre secondaire actuelle avant toute conclusion."
    if case['candidate_id'] == 'lego_11388':
        case['scenarios'] = [
            {'id': 'BUNDLE_ECONOMICS', 'type': 'CONDITIONAL_SCENARIO',
             'condition': "Le panier de lancement pourrait être compétitif si les recettes nettes réellement réalisables sur les cadeaux dépassent les remises alternatives et les frais.",
             'test': 'Comparer 499,99 € moins recettes nettes vérifiées des cadeaux au prix livré alternatif du set seul ; compter chaque cadeau une seule fois.',
             'invalidation': "Une meilleure remise sur le set seul, un cadeau absent du panier ou une faible valeur nette des cadeaux invaliderait cet avantage."}]
    elif case['candidate_id'] == 'lego_40889':
        case['scenarios'] = [
            {'id': 'EARLY_SECONDARY_SUPPLY', 'type': 'CONDITIONAL_SCENARIO',
             'condition': 'Des reventes de cadeaux pourraient créer une offre secondaire temporairement abondante.',
             'test': "Suivre les prix affichés, disponibilités et ventes conclues avant et après le 8 novembre ; ne pas confondre fin de promotion et fin d'offre secondaire.",
             'invalidation': "Une distribution prolongée, une demande insuffisante ou des frais absorbant l'écart rendraient ce pari peu intéressant."}]
    else:
        case['scenarios'] = [
            {'id': 'SEPARATE_GIFT_DEMAND', 'type': 'CONDITIONAL_SCENARIO',
             'condition': 'Une demande pour le taxi seul pourrait rencontrer les reventes des acheteurs du grand set.',
             'test': "Confirmer les conditions locales puis observer l'offre et la demande secondaires du taxi, sans attribuer sa valeur affichée à une recette certaine.",
             'invalidation': 'Une offre secondaire abondante, une vente séparée durable ou une prolongation de distribution affaiblirait la thèse de contrainte.'}]


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
    priorities = {'HIGH': 'Haute', 'MEDIUM': 'Moyenne', 'LOW': 'Faible'}
    actions = {'INVESTIGATE_EVENT': "Approfondir l'événement", 'MONITOR_OBSERVATIONS': 'Suivre les observations',
               'VERIFY_PRODUCT_CONTEXT': 'Vérifier le contexte du produit',
               'COMPARE_BUNDLE_AND_STANDALONE': 'Comparer panier avec cadeau et set seul',
               'COMPARE_SECONDARY_ACQUISITION': "Comparer l'acquisition secondaire",
               'VERIFY_REGIONAL_GIFT_TERMS': 'Confirmer les conditions françaises du cadeau'}
    actions['CHECK_POST_EVENT_MARKET'] = "Vérifier le marché après l'événement"
    gaps = {'REALIZED_SALES_NOT_CONNECTED': 'ventes conclues non connectées', 'LIQUIDITY_UNKNOWN': 'liquidité inconnue',
        'SUPPLY_AND_REPRINTS_UNKNOWN': 'offre globale et réimpressions inconnues',
        'RESALE_COSTS_AND_NET_MARGIN_UNKNOWN': 'coûts de revente et marge nette inconnus',
        'CAUSALITY_UNPROVEN': 'lien de causalité non établi', 'NO_RECENT_RETAIL_QUOTE': 'aucune offre récente collectée',
        'NO_PRODUCT_SPECIFIC_MANUFACTURER_PUBLICATION_IN_COLLECTED_EVIDENCE': 'aucune publication du fabricant liée à la référence dans les preuves collectées',
        'NO_MEASURED_EVENT_REACTION': "aucune réaction mesurée autour de l'événement", 'DELIVERED_PRICE_UNKNOWN': 'prix livré inconnu',
        'PROMOTION_TERMS_AND_REGION_NOT_VERIFIED': 'conditions et pays de la promotion non vérifiés',
        'BUNDLE_NET_ECONOMICS_UNKNOWN': 'rentabilité nette du panier inconnue',
        'GIFT_STACKING_UNCONFIRMED': 'cumul des cadeaux non confirmé',
        'SECONDARY_ACQUISITION_COST_UNKNOWN': "coût d'acquisition secondaire inconnu",
        'FRANCE_COMPLETE_GIFT_TERMS_UNCONFIRMED': 'conditions françaises complètes du cadeau non confirmées',
        'PRIMARY_CLAIMS_NOT_RECHECKED': 'vérification actuelle des conditions échouée ou texte modifié',
        'SOME_PRIMARY_CLAIMS_NOT_RECHECKED': 'certaines données primaires ne sont pas revérifiées actuellement',
        'FRENCH_CATALOGUE_PRICE_NOT_RECHECKED': 'prix de la fiche française non revérifié automatiquement'}
    lines = ['# EDGE — Dossiers de recherche des candidats', '',
        'Évaluation par règles explicites. Les priorités orientent la recherche ; elles ne prédisent pas le rendement.', '',
        '| Référence | Priorité de recherche | Action | Révision |', '|---|---|---|---|']
    for case in report['assessments']:
        lines.append(f"| {case['sku']} | {priorities[case['research_priority']]} | {actions[case['research_action']]} | {case['revision']} |")
    expanded = [c for c in report['assessments'] if c.get('primary_verification')]
    for case in (expanded or report['assessments'][:3]):
        lines += ['', '## Référence ' + case['sku'], '', '**Pourquoi poursuivre la recherche**', ''] + ['- ' + reason for reason in case['reasoning']]
        lines += ['', '**Hypothèse précoce, non validée**', '', case['early_hypothesis']['statement'], '',
                  '**Contre-hypothèse**', '', case['early_hypothesis']['counter_hypothesis'], '',
                  '**Prochaine vérification**', '', case['next_check'], '', '**Preuves**', '']
        for fact in case['facts']:
            if fact['type'] == 'PUBLICATION_REFERENCE':
                title = fact['title'].replace('[', '(').replace(']', ')')
                role = 'fabricant' if fact['source_role'] == 'MANUFACTURER' else 'média spécialisé'
                lines.append('- [' + title + '](' + fact['source_url'] + ') — ' + role)
            elif fact['type'] == 'RETAIL_OBSERVATION':
                stock = {'IN_STOCK': 'en stock', 'OUT_OF_STOCK': 'en rupture', 'UNKNOWN': 'inconnu'}.get(fact['availability'], fact['availability'])
                lines.append('- Dernier prix observé : ' + fact['price'] + ' ' + fact['currency'] + ' ; stock déclaré : ' + stock + ' ; relevé : ' + fact['observed_at'])
            elif fact['type'] == 'VERIFIED_PRIMARY_CLAIM':
                lines.append('- [Condition officielle vérifiée](' + fact['source_url'] + ') : ' + claim_text(fact['claim']))
        lines += ['', '**Acteurs : motivations possibles, non vérifiées**', '']
        if case.get('secondary_market_evidence'):
            rows = case['secondary_market_evidence']['listings']
            lines += ["- Offres secondaires : " + str(len(rows)) + " cartes d'annonces capturées ; aucune livraison en France ni recette nette vérifiée. [Voir le relevé et les seuils conditionnels](economics_report.md)."]
        lines += ['- ' + actor['hypothesis'] for actor in case['actor_hypotheses']]
        lines += ['', '**Scénarios à tester**', '']
        for scenario in case['scenarios']:
            lines += ['- ' + scenario['condition'] + ' Vérification : ' + scenario['test'] + ' Invalidation : ' + scenario['invalidation']]
        lines += ['', '**Manques** : ' + ', '.join(gaps[g] for g in case['missing_data']), '',
                  'Avantage économique : non démontré. Décision financière : non évaluée.']
    return '\n'.join(lines) + '\n'


def claim_text(claim):
    kind = claim['kind']
    if kind == 'PUBLISHED_CATALOGUE_PRICE':
        return 'prix catalogue de ' + claim['value'] + ' ' + claim['currency'] + ', sans preuve de commande exécutable.'
    if kind == 'PUBLISHED_RECOMMENDED_PRICE_EUR':
        return 'prix annoncé de ' + claim['value'] + ' ' + claim['currency'] + ' dans le communiqué du fabricant, sans preuve de commande exécutable.'
    if kind == 'ANNOUNCED_EARLY_ACCESS':
        return 'accès anticipé annoncé le ' + claim['date'] + ' pour les membres ' + claim['membership_required'] + '.'
    if kind == 'ANNOUNCED_GENERAL_RELEASE':
        return 'sortie générale annoncée le ' + claim['date'] + '.'
    if kind in ('ANNOUNCED_LINKED_GIFT', 'ANNOUNCED_CONDITIONAL_GIFT'):
        return 'cadeau 40898 annoncé avec le 11388 du ' + claim['start_date'] + ' au ' + claim['end_date'] + ', sous réserve de stock ; conditions françaises complètes à confirmer.'
    if kind == 'GIFT_ELIGIBILITY':
        return 'cadeau en France dès ' + claim['minimum_spend_eur'] + ' € de marchandises LEGO, du ' + claim['start_date'] + ' au ' + claim['end_date'] + ', un par foyer, sous réserve de stock.'
    if kind == 'APPROXIMATE_PROMOTIONAL_VALUE':
        return 'valeur promotionnelle approximative de ' + claim['value'] + ' ' + claim['currency'] + ', sans valeur de revente démontrée.'
    return 'le cadeau doit être retourné avec les achats éligibles remboursés.'


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
    primary_path = out / 'primary_verifications.json'
    primary = json.loads(primary_path.read_text()) if primary_path.exists() else None
    secondary_path, economics_path = out / 'secondary_market.json', out / 'bundle_economics.json'
    secondary = json.loads(secondary_path.read_text()) if secondary_path.exists() else None
    economics = json.loads(economics_path.read_text()) if economics_path.exists() else None
    observed = now()
    cases = [assess(c, market, markets, reaction, publications, observed, primary, secondary, economics) for c in discovery['candidates']]
    order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    cases.sort(key=lambda c: (order[c['research_priority']], c['candidate_id']))
    transitions = assign_revisions(cases, previous, observed)
    report = {'schema': 'edge.mri.research_assessments.v1', 'observed_at': observed,
              'assessment_method': 'DETERMINISTIC_EVIDENCE_RULES_V1', 'assessments': cases,
              'transitions': transitions, 'status': 'OK' if cases else 'EMPTY',
              'financial_decisions_made': 0, 'purchase_authorized': False}
    market['coverage']['candidate_assessments'] = len(cases)
    market['coverage']['assessment_status'] = report['status']
    market['coverage']['primary_review_matches'] = sum(c.get('primary_verification', {}).get('status') == 'REVIEWED_CLAIMS_RECHECKED' for c in cases)
    market['coverage']['primary_review_partial_matches'] = sum(c.get('primary_verification', {}).get('status') == 'REVIEWED_CLAIMS_PARTIALLY_RECHECKED' for c in cases)
    if primary:
        verified_count = sum(s['status'] == 'VERIFIED_MATCH' for s in primary['sources'])
        status = 'OK' if verified_count == len(primary['sources']) else 'PARTIAL' if verified_count else 'FAILED'
        market['coverage']['primary_source_recheck_status'] = status
        if status != 'OK' and market['status'] == 'OK':
            market['status'] = 'PARTIAL'
    (out / 'report.json').write_text(json.dumps(market, indent=2, ensure_ascii=False))
    (out / 'assessments.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
    (out / 'assessment_report.md').write_text(render(report))
    manifest = {p.name: digest(p.read_bytes()) for p in out.iterdir() if p.is_file() and p.name != 'manifest.json'}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps({'assessed_candidates': len(cases), 'priorities': {p: sum(c['research_priority'] == p for c in cases) for p in order},
                      'financial_decisions': 0}))


if __name__ == '__main__':
    main()
