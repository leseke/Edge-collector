# EDGE MRI-001 — Market Reaction Intelligence (prototype hors ligne)

## Objectif
Comprendre des événements publics et proposer **des hypothèses concurrentes** avant confirmation des prix. Ce lot ne fournit ni analyse autonome du web ni recommandation d'achat. Une rareté des données n'interdit pas l'hypothèse; elle interdit seulement de présenter son résultat comme établi.

## Fonctions livrées
- `validate_event` et `validate_measure` : observations horodatées, identifiants source, refus des champs d'allocation et des ventes sans marqueur de preuve.
- `snapshot` : reconstruit **ce qui était connu** au temps T avec `observed_at`, pas uniquement `occurred_at`. Protection contre le *look-ahead bias*.
- `make_hypothesis` : thèse, explication rivale, prédictions mesurables, invalidation et risques. Jamais une décision économique.
- `event_window` : statistiques observées avant/après sans inventer d'historique, avec références d'observation et avertissement causal.
- `assess_prediction` : `PENDING`, `NO_DATA`, `SUPPORTED`, `NOT_SUPPORTED`. Un résultat soutenu ne démontre ni causalité ni rentabilité. Les évaluations ne sont pas des probabilités.

## Gouvernance
Aucun réseau, fournisseur payant, secret, journal financier, déploiement ou modification de `edge_engine.py`. L'étiquette `verified_sale` de l'interface n'est PAS une vérification cryptographique de transaction; elle suppose une qualification préalable dans la couche Evidence Discovery. Une validation en production devra vérifier l'identité des sources et la non-réécriture des événements. Les acteurs et leurs publications publics ne sont pas des motifs de profiler des personnes privées.

## Limites à résoudre avant MRI-002
- Les hypothèses sont soumises comme texte structuré, pas générées par une véritable IA dans ce lot.
- Les variables exogènes et événements simultanés ne sont pas ajustés ; aucune inférence causale.
- La normalisation des entités, la segmentation géographique et les groupes témoins sont à concevoir.
- `flat` signifie variation strictement zéro : remplacer par une bande de tolérance calibrée à l'avenir.
- Les observations historiques sont en mémoire pour le prototype et ne sont pas persistées ici. Prévoir append-only raccordé au registre existant.
- Les scores de conviction ne sont volontairement pas introduits sans historique de calibration.

## Vérification
`python -m unittest tests.test_market_reaction -v`
`python -m tools.run_tests_offline`

## Scénario de démonstration
Le test `test_late_discovery_does_not_rewrite_backtest` utilise des données **fictives** (mentions 10→30), tandis qu'une ancienne observation connue plus tard (999) est exclue du rejeu. Le test de prédiction conserve `PENDING` tant que sa période n'est pas terminée.
