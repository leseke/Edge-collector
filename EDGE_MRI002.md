# EDGE MRI-002 — Actor Intelligence (prototype isolé)

## Objectif
Construire une interprétation **hypothétique** des actions publiques d'acteurs de marché avant la confirmation des prix. L'acteur peut être une marque, plateforme, distributeur, éditeur, communauté publique ou créateur public. Le module ne profile pas des personnes privées, ne prétend pas connaître les intentions, et ne donne aucune recommandation financière.

## Fonctions
- `validate_actor` : acteurs publics, refus de champs privés sensibles.
- `validate_action` : événement sourcé avec date réelle et date à laquelle EDGE en a eu connaissance.
- `build_actor_brief(..., as_of=...)` : conserve uniquement les événements connus à la date du rejeu.
- `propose_scenarios` : thèse et scénario rival distincts, mécanisme supposé, preuves connues, critères d'invalidation, horizon de 1 à 365 jours. `policy_decision` reste `NOT_EVALUATED`.
- Identifiant d'hypothèse déterministe. Aucune preuve, motivation ou statistique inventée.

## Vérifications
`python -m unittest tests.test_actor_intelligence -v`

8 tests ciblés exécutés localement sur le même contrat, 8 réussis. La suite complète EDGE et le contrôle de non-divulgation restent à lancer sur cette branche. Pas de réseau, d'API OpenAI ni de dépenses pendant les tests.

## Limites
Prototype sans moteur LLM, collecte réelle, scores probabilistes, classement des acteurs ni stockage durable des thèses. Ne conclut pas à la causalité et ne remplace pas MRI-001. L'interprétation comportementale demeure explicitement incertaine; elle ne doit pas être un prétexte au profilage personnel.

## Statut GitHub
Branche `edge/mri-002-actor-intelligence` créée depuis MRI-001 commit `37e1dc23032a8838b201ce7f06680afbcd8b1ea2`. `main` inchangé, pas de déploiement ni fusion.
