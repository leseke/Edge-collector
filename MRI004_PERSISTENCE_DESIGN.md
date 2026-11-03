# MRI-004.3 — Contrat de persistance durable

Statut : conception validée localement, backend distant NON provisionné  
Branche de travail : `edge/mri-004-continuity-notification-contract`  
Périmètre : journal d'exécution et continuité de surveillance uniquement

## Décision provisoire

Évaluer en premier un dépôt GitHub **privé et distinct** comme journal durable append-only. Le dépôt applicatif `leseke/Edge-collector` est public : aucune donnée opérationnelle privée, aucun heartbeat détaillé et aucune donnée financière ne doivent y être écrits.

Aucun dépôt privé n'est créé par ce changement. Aucun jeton n'est demandé, créé ou configuré. Aucun workflow de collecte n'est activé.

## Comparaison des options

| Option | Avantages | Limites / risques | Décision |
|---|---|---|---|
| Dépôt GitHub privé dédié | Pas de service DB à provisionner, historique versionné, export simple, séparation des accès | Jeton finement limité nécessaire pour un dépôt distinct ; écritures concurrentes à sérialiser ; commits plus lourds qu'une DB | Premier candidat |
| Base hébergée (Supabase/Postgres ou équivalent) | Requêtes temporelles, contraintes uniques, transactions et concurrence mieux adaptées | Provisionnement, secrets, limites et éventuels coûts à vérifier ; nouvelle dépendance | Garder comme option si volume ou concurrence le justifie |
| Artifacts GitHub Actions | Simple pour exporter un diagnostic ponctuel | Rétention limitée, récupération et agrégation moins adaptées à un journal long terme | Audit temporaire seulement |
| SQLite du runner | Déjà implémenté et testé | Détruit avec le runner ; aucune continuité inter-exécutions | Cache local uniquement |

## Données autorisées

Le journal distant ne contient que des métadonnées de surveillance minimales :

- identifiant opaque du run et tentative ;
- événement STARTED / FINISHED / ABORTED (ABORTED est une interprétation calculée, pas une écriture rétroactive) ;
- horodatage UTC de l'événement ;
- déclencheur et révision du code ;
- statut global du run ;
- sources attendues / en échec sous forme d'identifiants techniques ;
- compteurs de résultats non financiers ;
- identifiant de schéma.

Interdits : capital, portefeuille, prix d'achat personnel, allocations, identifiants de compte, clés, jetons, URL privées, données personnelles, message brut d'exception, payloads fournisseurs, offres détaillées ou contenu de notification.

La liste blanche actuelle de `storage.py` reste la référence minimale ; tout élargissement exige un changement explicite et des tests anti-fuite.

## Format logique

Un événement est immuable et possède au minimum :

- `schema_version`
- `event_id` (UUID)
- `run_id`
- `attempt`
- `event_type`
- `occurred_at_utc`
- `code_revision`
- `payload` validé par liste blanche

L'identité d'idempotence est `(run_id, attempt, event_type)`. Un rejeu ne doit jamais créer un second STARTED ou FINISHED. Un conflit doit être relu et réconcilié, jamais résolu par écrasement aveugle.

## Écritures et concurrence

Pour un backend Git :

1. lire la tête courante et le manifeste de séquence ;
2. préparer un nouvel événement avec un identifiant déterministe/idempotent ;
3. tenter une mise à jour conditionnelle basée sur le SHA courant ;
4. en cas de conflit, relire puis vérifier si l'événement existe déjà ;
5. réessayer avec un nombre borné de tentatives ;
6. si l'écriture échoue, conserver un état local exportable et signaler la continuité comme INCONNUE, jamais comme OK.

Ne jamais forcer un push, réécrire l'historique, supprimer un événement, ni accepter une divergence silencieuse.

Le format de stockage devra être partitionné par date UTC (par exemple `events/YYYY/MM/DD.jsonl`) avec des lots petits et bornés. Le manifeste n'est qu'un index reconstructible, pas la source de vérité.

## Continuité : distinction essentielle

Le heartbeat indique qu'un processus a commencé ou terminé. Il ne prouve pas qu'une source de marché a été interrogée ni qu'une fenêtre est couverte.

Chaque fenêtre attendue devra être évaluée séparément :

- `OBSERVED` : interrogation réussie et observation horodatée dans la fenêtre ;
- `NO_REACTION_OBSERVED` : interrogation réussie, aucune réaction admissible trouvée ;
- `SOURCE_FAILED` : tentative faite mais source en erreur ;
- `NOT_SCHEDULED` : aucune interrogation n'était prévue ;
- `MISSED` : fenêtre attendue, aucune tentative connue ;
- `UNKNOWN` : journal incomplet, horloge incertaine ou persistance non vérifiée.

Une absence de données n'est jamais automatiquement une absence de réaction.

Les heures planifiées doivent venir d'un calendrier de scheduler vérifiable, avec timezone UTC et identifiant de fenêtre. Ne pas déduire `scheduled_at` de l'heure réelle de démarrage.

## Séquence de validation avant activation

1. [FAIT] Formaliser un protocole `RunJournal` indépendant du backend dans `intelligence/run_journal.py`.
2. [FAIT] Encapsuler SQLite dans `SQLiteRunJournal`, sans changer le collecteur ni la persistance active.
3. [FAIT] Ajouter `InMemoryRemoteJournal`, simulateur sans réseau avec compare-and-swap, événements immuables, clé idempotente et retries bornés.
4. [FAIT] Couvrir les écritures concurrentes, les réponses perdues après commit, les doublons altérés, l'absence de STARTED, les champs privés et l'indisponibilité.
5. [FAIT] Faire échouer en mode prudent l'évaluation de continuité lorsque `journal_status` n'est pas explicitement `VERIFIED` : compteurs et couverture restent inconnus.
6. [EN VALIDATION CI] Exécuter la suite complète avec ces nouveaux tests.
7. [À FAIRE] Vérifier une reconstruction multi-runs de bout en bout depuis un flux d'événements restauré.
8. Provisionner un dépôt privé uniquement après accord explicite et créer un jeton à portée minimale.
9. Tester lecture/écriture sur un jeu synthétique non sensible, puis vérifier restauration depuis zéro et comportement en cas de journal inaccessible.
10. Seulement ensuite, envisager une cadence planifiée distincte, avec limites de coûts et arrêt d'urgence.

## Critères d'acceptation

- Aucun changement à `main`.
- Aucun journal privé dans le dépôt public.
- Aucun secret dans le code, les logs ou les artefacts.
- Idempotence démontrée sur retry.
- Concurrence démontrée avec deux writers.
- Échec du backend => statut de continuité UNKNOWN / DEGRADED, jamais fausse couverture.
- Restauration complète depuis le backend distant démontrée.
- Aucun appel fournisseur payant ni cadence nocturne activé par cette étape.

## MRI-004.4 — Résultat de la simulation

Le simulateur est un modèle de test en mémoire, pas une persistance réelle. Il valide le protocole de concurrence optimiste : un writer avec une tête périmée reçoit un conflit, relit et réessaie ; un rejeu identique après une réponse perdue ne crée pas de doublon ; un contenu différent sous la même clé idempotente est rejeté.

`assess_continuity()` exige désormais `journal_status="VERIFIED"` pour produire des compteurs de couverture. Sa valeur par défaut est `UNKNOWN`. Si le journal est `DEGRADED`, `UNAVAILABLE` ou `UNKNOWN`, EDGE masque les compteurs d'observation et n'affiche aucune couverture calculée sur un historique potentiellement incomplet.

## Limite de cette livraison

Cette livraison valide un contrat et un simulateur. Elle ne rend pas encore le journal durable : le dépôt privé, le credential, l'adaptateur distant réel, la reconstruction bout en bout depuis un historique distant et le scheduler restent absents.
