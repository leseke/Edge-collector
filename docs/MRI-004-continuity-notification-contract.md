# MRI-004 — Contrat de continuité et de notification Radar EDGE

Statut : spécification de travail, non exécutée en production.

Branche : `edge/mri-004-continuity-notification-contract`  
Base : `edge/mri-003-historical-evidence-gate`

## 1. Objectif

Produire des notifications décisionnelles utiles à l'utilisateur sans confondre :
- absence de changement observé ;
- absence d'observation ;
- donnée ancienne ;
- source indisponible ;
- hypothèse anticipative.

Le moteur doit pouvoir signaler une piste à approfondir même si la décision financière reste WATCH / ATTENDRE et l'allocation proposée à zéro.

## 2. Contrat de continuité

Chaque exécution planifiée doit produire un heartbeat indépendant du succès des collecteurs.

Champs minimaux d'un heartbeat :
- `run_id`
- `scheduled_at` : heure théorique attendue, ISO-8601 UTC
- `started_at`
- `completed_at`
- `run_status` : OK | PARTIAL | FAILED | EMPTY
- `sources_expected[]`
- `sources_started[]`
- `sources_succeeded[]`
- `sources_failed[]`
- `products_expected[]`
- `products_observed[]`

Une exécution qui démarre mais ne collecte rien n'est pas une observation de marché.

### Fenêtres temporelles

Pour chaque source et produit surveillés, calculer :
- `last_success_at`
- `last_observation_at`
- `expected_interval_minutes`
- `observation_age_minutes`
- `missed_windows`
- `longest_gap_minutes`
- `coverage_ratio`
- `continuity_status` : CONTINUOUS | DEGRADED | GAP | UNKNOWN

Règles :
1. Une fenêtre est observée uniquement si une capture exploitable existe dans sa tolérance temporelle.
2. Un heartbeat sans donnée produit ne remplit pas une fenêtre d'observation du marché.
3. Une source en erreur crée une fenêtre manquée, pas un signal de baisse ou d'absence de demande.
4. Aucune interpolation ne doit transformer un trou en observation.
5. Les horaires planifiés et les horaires réellement capturés sont conservés séparément.
6. Toute mesure de continuité porte une période explicite et une cadence attendue.

## 3. Contrat de preuve MRI

Chaque preuve attachée à une piste doit porter :
- `claim_id`
- `claim`
- `evidence_type` : OFFICIAL_PRIMARY | DIRECT_MARKET | SOLD_TRANSACTION | RETAIL_OFFER | COMMUNITY_SIGNAL | AGGREGATOR
- `epistemic_status` : FACT | SIGNAL | INFERENCE | HYPOTHESIS | UNKNOWN
- `source_name`
- `source_url`
- `published_at` (si connu)
- `observed_at`
- `captured_at`
- `valid_until` (si applicable)
- `independent_source_group`
- `confidence` (optionnel, borné 0..1, jamais présenté comme une probabilité objective sans calibration)

Une répétition d'une même dépêche ou d'un même communiqué par plusieurs sites ne constitue pas plusieurs sources indépendantes.

Les prix doivent distinguer au minimum :
- prix affiché / offre ;
- prix de précommande ;
- prix de vente réalisée ;
- estimation ;
- prix historique.

Un prix affiché ne doit jamais être présenté comme une transaction conclue.

## 4. Mesure des réactions autour d'un événement

Chaque événement suivi doit définir :
- `event_id`
- `event_type` : ANNOUNCEMENT | PREORDER_OPEN | RELEASE | RESTOCK | RETIREMENT | REPRINT | PRICE_CHANGE | COMMUNITY_EVENT
- `event_at`
- `event_source`
- `pre_window`
- `post_windows[]`
- `expected_metrics[]`

Mesures possibles par fenêtre :
- volume de publications et d'auteurs uniques ;
- évolution des recherches, si la source fournit une mesure comparable ;
- nombre d'offres et disponibilité observée ;
- prix demandés ;
- transactions réalisées et nombre de ventes ;
- délai de vente / liquidité, uniquement si mesurable ;
- dispersion des prix ;
- évolution des stocks, avec source et couverture.

Pour chaque métrique, conserver valeur, unité, source, période, couverture et statut de preuve.

Une métrique sans couverture suffisante est UNKNOWN, jamais zéro.

Aucune causalité ne doit être affirmée sur la seule base d'une variation postérieure à l'événement. Employer « corrélé temporellement » ou « compatible avec » tant que la causalité n'est pas établie.

## 5. Format de notification utilisateur

### En-tête radar
- date et heure de génération ;
- nombre de nouvelles asymétries à approfondir ;
- allocation proposée agrégée, si elle est calculable et autorisée dans le canal ;
- posture générale du radar.

### Carte de piste
1. Nom du produit / licence / référence.
2. Décision courte : ACHETER | ATTENDRE | SURVEILLER | ABANDONNER.
3. Présentation commerciale : format, prix, vendeur, livraison, stock, date de sortie.
4. Pourquoi la piste mérite l'attention : catalyseur, anomalie et fenêtre temporelle.
5. Vérifications commerciales : chaque offre avec URL, prix, frais, vendeur et état de vérification.
6. Décision EDGE : prix d'entrée, ventes réalisées, ROI net, horizon, catégorie FLIP / HOLD / FUTURE_CLASSIC, allocation proposée.
7. Pourquoi maintenant : événement et échéance vérifiables.
8. Contre-thèse : éléments qui affaiblissent l'hypothèse.
9. Perte possible : scénario de perte et hypothèses explicites.
10. Invalidation : conditions observables qui font abandonner ou reclasser la piste.
11. Qualité des preuves : faits, signaux, inférences, hypothèses, inconnus.
12. Continuité : période couverte, fenêtres attendues, fenêtres observées, trous et âge des preuves.
13. Sources : liens directs, dates et nature de chaque source.

### Autres changements constatés

Ne montrer que les changements matériels depuis la notification précédente :
- changement de prix ou de stock ;
- apparition/disparition d'une offre ;
- nouvelle preuve ;
- changement de qualité ou fraîcheur ;
- franchissement de seuil ;
- changement de décision ;
- invalidation ou réactivation.

Une absence de changement ne doit être annoncée que si la couverture de surveillance est suffisante. Sinon afficher « aucune évolution vérifiable — couverture insuffisante ».

### État des preuves et du capital

Séparer explicitement :
- données observées ;
- données non disponibles ;
- calculs effectivement exécutés ;
- ROI non calculable ;
- allocation proposée ;
- capital réellement disponible, uniquement dans un canal privé autorisé.

## 6. Règles de confidentialité

Les clés financières privées (`treasury`, `engaged`, `capital_available`, `capital_monthly`, allocations privées en euros) ne doivent jamais fuiter dans `radar.json`, GitHub Pages, les logs publics ou les messages Telegram tant que le canal n'a pas été explicitement conçu et vérifié comme privé.

Le contrat de notification peut afficher une allocation proposée de 0 € si elle découle de la décision économique. Il ne doit pas déduire ni révéler le cash réel disponible.

L'interface utilisateur ne doit pas exposer les détails de maintenance, empreintes, journaux d'exécution ou diagnostics internes.

## 7. Tests d'acceptation obligatoires

1. Un heartbeat réussi sans capture produit ne compte pas comme observation de marché.
2. Une fenêtre sans capture est comptée comme manquée.
3. Une panne source ne devient jamais une variation de demande.
4. Une absence de publication n'est pas un signal négatif si la collecte est incomplète.
5. Une preuve ancienne est signalée comme ancienne même si elle est toujours accessible.
6. Une offre et une vente réalisée restent deux types de prix distincts.
7. Deux reprises d'une même source ne comptent pas comme deux confirmations indépendantes.
8. Une métrique absente reste UNKNOWN, pas zéro.
9. Un événement sans mesures pré-événement ne permet pas de prétendre mesurer un effet avant/après.
10. Les notifications publiques ne contiennent aucune donnée financière privée.
11. Les notifications ne peuvent afficher « aucune évolution » que si la couverture de la période est suffisante.
12. Une hypothèse et une inférence sont toujours étiquetées comme telles.

## 8. Ordre d'implémentation

1. Ajouter le journal de heartbeats et les calculs de fenêtres manquées.
2. Ajouter les tests de trous, de fraîcheur et de couverture.
3. Relier les preuves et les événements MRI aux fenêtres temporelles.
4. Ajouter le rendu de notification à partir des données structurées.
5. Vérifier les sorties publiques et privées par tests anti-fuite.
6. Exécuter la suite de tests hors réseau avant toute promotion de branche.

Aucun déploiement, envoi Telegram, achat de données payantes ou modification de `main` n'est autorisé par cette spécification.
