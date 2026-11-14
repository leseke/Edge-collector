# MRI-004.16 — Persistance durable du journal

Statut : architecture MVP définie ; backend réel NON provisionné ; aucune collecte activée
Branche : `edge/mri-004-continuity-notification-contract`
Périmètre : persistance des événements de continuité uniquement

## 1. Décision d'architecture

Le premier backend cible est un **dépôt GitHub privé dédié**, distinct du dépôt applicatif public `leseke/Edge-collector`.

Le journal est stocké sous forme d'un événement JSON immuable par fichier :

`events/YYYY/MM/DD/<event_id>.json`

Le fichier est créé une seule fois. Il n'est jamais mis à jour ni supprimé. Le partitionnement UTC facilite la restauration par période et évite un fichier JSONL partagé dont chaque écriture concurrente exigerait une mise à jour de SHA commune.

Le manifeste éventuel est un index reconstructible ; il n'est jamais la source de vérité. La vérité est l'ensemble des fichiers événementiels valides du dépôt privé.

Aucune base distante, aucun dépôt privé, aucun jeton et aucun workflow de collecte ne sont créés ou activés par cette étape.

## 2. Pourquoi ce choix

- Pas de base payante à provisionner pour le MVP.
- Historique versionné et restauration depuis un dépôt vide local.
- Un fichier par événement évite le verrou global d'un journal JSONL partagé.
- Les créations concurrentes de fichiers distincts ne se remplacent pas.
- Une collision sur le même `event_id` est traitée comme un rejeu : relire le fichier existant et comparer l'événement canonique octet/logiquement ; identique = succès idempotent, différent = erreur d'intégrité.
- Aucun écrasement, force-push, rebase ou réécriture de l'historique n'est autorisé.

Limites assumées : latence et quotas API GitHub, coût de commits croissant, restauration nécessitant une pagination complète, dépendance à GitHub et besoin d'un credential à portée restreinte. Si le volume ou la concurrence deviennent importants, réévaluer une base transactionnelle hébergée avant d'atteindre les limites.

## 3. Contrat d'écriture

1. Valider strictement l'événement et sa liste blanche de champs avant tout accès réseau.
2. Construire un identifiant déterministe à partir de la clé d'idempotence : `(run_id, attempt, event_type)`, complétée par `(window_id, source_id)` pour `SOURCE_RESULT`.
3. Construire le chemin à partir de l'horodatage UTC immuable de l'événement et de son `event_id`.
4. Tenter une création de fichier, jamais une mise à jour.
5. Si le chemin existe ou si la réponse est ambiguë, relire le fichier :
   - événement strictement identique : considérer l'écriture comme déjà validée ;
   - contenu différent : erreur d'intégrité, aucune réparation automatique.
6. Pour un conflit transitoire, relire l'état puis réessayer avec un nombre borné de tentatives et un délai borné.
7. Si le backend est indisponible ou si l'état du commit ne peut être établi, signaler `UNAVAILABLE` ou `UNKNOWN`. Ne jamais fabriquer une couverture.

L'ordre métier est validé au niveau du run : exactement un `STARTED`, zéro ou plusieurs `SOURCE_RESULT` après STARTED, puis au plus un `FINISHED`. Les événements doivent aussi respecter l'ordre chronologique vérifié par le reconstructeur. Une tentative possède un `run_id` distinct dans le schéma SQLite actuel ; l'adaptateur distant conserve explicitement `attempt`.

## 4. Contrat de restauration

- Lire toutes les partitions demandées, en suivant toutes les pages de l'API.
- Valider le chemin, le schéma, l'identité, les horodatages et la liste blanche de chaque événement.
- Rejeter les doublons contradictoires, les événements malformés et les collisions d'identité.
- Trier de façon déterministe, puis rejouer le flux avec `verify_run_history` et `reconstruct_windows`.
- Ne déclarer `VERIFIED` que si l'inventaire de la période est complet, les pages ont toutes été lues et les contrôles d'intégrité passent.
- Une erreur de pagination, une permission insuffisante, un trou de partition ou une réponse partielle entraîne `DEGRADED` / `UNKNOWN` et masque les ratios.

La restauration doit pouvoir être exécutée depuis un environnement vierge, sans dépendre du SQLite du runner précédent.

## 5. Sécurité et données autorisées

Données autorisées : identifiants opaques de run/tentative, type d'événement, horodatage UTC, révision de code, déclencheur, fenêtre, identifiants techniques de sources, statut global et résultats source minimaux.

Données interdites : capital, portefeuille, prix d'achat personnel, allocation, données de compte, PII, secrets, jetons, URL privées, payloads fournisseurs, annonces/offres détaillées, messages bruts d'exception et contenu de notification.

Le dépôt de journal doit être privé et séparé. Le credential ne doit jamais être commité, affiché, inclus dans les logs ou transmis dans une conversation. Pour le futur branchement GitHub Actions, préférer une GitHub App limitée à ce dépôt ; à défaut, un jeton finement limité au seul dépôt privé et aux permissions Contents nécessaires, stocké comme secret d'environnement protégé. Aucun jeton ne doit être demandé dans le chat.

## 6. Provisionnement requis avant l'adaptateur réel

Action humaine requise :
1. Créer un dépôt GitHub privé distinct, par exemple `edge-private-journal`.
2. Ne lui donner aucun historique ou fichier de données personnel au départ.
3. Configurer une identité d'écriture limitée à ce seul dépôt privé, avec accès Contents minimal.
4. Stocker le credential dans un secret d'environnement GitHub protégé du dépôt applicatif ; ne pas le coller dans le code ou la conversation.
5. Communiquer uniquement le nom `owner/repository` du dépôt privé, jamais le jeton.

Tant que ces étapes ne sont pas réalisées, l'adaptateur distant reste désactivé et le statut de continuité ne peut pas devenir `VERIFIED` à partir de SQLite local.

## 7. Matrice de validation avant activation

| Scénario | Résultat exigé |
|---|---|
| Création événement neuf | Un fichier immuable |
| Rejeu identique après réponse perdue | Succès idempotent, un seul fichier |
| Même clé, contenu différent | Erreur d'intégrité |
| Deux runs concurrents | Les deux événements sont conservés |
| Deux writers même événement | Un seul fichier, même contenu accepté |
| Backend indisponible | UNKNOWN / UNAVAILABLE, ratios masqués |
| Pagination incomplète | DEGRADED / UNKNOWN |
| Fichier malformé ou chemin incohérent | Rejet, aucune couverture vérifiée |
| Restauration depuis environnement vierge | Historique complet identique |
| STARTED sans FINISHED | Run interrompu détecté, jamais transformé en observation |
| Donnée privée dans payload | Rejet avant réseau |

Tous les tests doivent utiliser un faux transport HTTP local ou des réponses enregistrées. Aucun test CI ne doit écrire dans le dépôt privé ou appeler un fournisseur de marché.

## 8. État et prochaine étape

Cette étape fixe le format durable cible et ses garanties, mais **ne prétend pas fournir une persistance opérationnelle**. L'accès au dépôt privé est un prérequis externe et nécessite une action explicite.

Après provisionnement et transmission du seul nom du dépôt :
- implémenter l'adaptateur GitHub privé derrière le protocole journal ;
- ajouter un transport simulé et des tests de panne, concurrence, idempotence et restauration ;
- vérifier les permissions minimales et les limites de pagination ;
- effectuer un test synthétique contrôlé seulement après accord explicite ;
- garder le scheduler et les collecteurs désactivés jusqu'à validation indépendante.
