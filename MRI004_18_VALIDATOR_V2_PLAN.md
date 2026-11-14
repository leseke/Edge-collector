# MRI-004.18 — Plan du validateur d'événements v2

Statut : **plan d'implémentation et contrat de tests — documentation uniquement**  
Dépendance normative : `MRI004_17_PROTOCOL_V2.md`  
Branche cible : `edge/mri-004-continuity-notification-contract`

## 1. Objectif et périmètre

Construire le premier composant v2 de manière isolée et déterministe : validation d'un événement individuel, canonicalisation, identité, hash, chemin de stockage et validation de chaîne. Cette étape ne réalise aucun accès réseau ni écriture GitHub.

Ordre :
1. fixer les détails de schéma ci-dessous ;
2. implémenter canonicalisation et validateurs purs ;
3. exécuter les tests offline unitaires ;
4. ajouter une seconde implémentation indépendante des vecteurs ;
5. seulement après revue, intégrer le validateur au transport simulé 004.17-C.

Aucun changement à `collect.py`, `storage.py`, au scheduler, aux connecteurs ou à la branche `main`.

## 2. Décisions de précision à appliquer au protocole

### 2.1 Domaine canonique v2

Le journal est un protocole machine-à-machine, pas un espace de texte libre.

- Toutes les clés JSON sont ASCII.
- Toutes les chaînes de valeurs v2 sont ASCII et limitées aux champs/regex de leurs validateurs.
- Aucun flottant, NaN, Infinity, nombre exponentiel ou entier booléen.
- Les entiers sont des entiers JSON dans l'intervalle 0 à 2^31-1, sauf `attempt` qui commence à 1.
- Les objets JSON ne peuvent contenir de clés dupliquées.
- Aucun champ non prévu par le schéma n'est accepté.
- Encodage UTF-8 sans BOM ; comme le domaine v2 est ASCII, toute valeur non ASCII est rejetée.
- Sérialisation : clés triées lexicographiquement, séparateurs compacts, aucun espace superflu, aucun saut de ligne final.

Cette restriction évite les ambiguïtés de tri Unicode, de normalisation et de représentation numérique entre langages. Si du texte humain devient un jour nécessaire, il devra être stocké hors du journal d'événements ou introduit par une version de schéma distincte.

### 2.2 Identifiants

Valeurs proposées :
- `run_id` : 1 à 128 caractères ASCII, regex `[A-Za-z0-9][A-Za-z0-9._:-]{0,127}`.
- `window_id` : 1 à 128 caractères ASCII, même regex.
- `source_id` : 1 à 128 caractères ASCII, regex `[A-Za-z0-9][A-Za-z0-9._:-]{0,127}`.
- `trigger` : `manual` ou `schedule`.
- `attempt` : entier strict 1 à 2^31-1.
- `sequence` : entier strict 0 à 2^31-1.
- `schema_version` : entier strict égal à 2.

Un booléen Python ne doit jamais être accepté comme entier, même si `isinstance(True, int)` est vrai.

### 2.3 Horodatage

Regex lexicale exacte : `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{6}Z$`.

La validation doit également parser le calendrier réel : date impossible, heure hors plage ou seconde invalide rejetée. UTC obligatoire. Pas d'offset, pas de timestamp naïf, pas de précision variable.

Les timestamps d'une chaîne doivent être **non décroissants** selon sequence. La séquence reste l'ordre faisant autorité ; deux événements consécutifs peuvent partager la même microseconde.

### 2.4 Payload STARTED exact

Champs racine : `trigger`, `scheduled_at`, `window_id`, `expected_sources`.

- `trigger=manual` : `scheduled_at=null`, `window_id=null`, `expected_sources=[]`.
- `trigger=schedule` : `scheduled_at` canonique non nul, `window_id` non vide, `expected_sources` non vide.
- `expected_sources` : liste de source_id sans doublon, triée lexicographiquement avant sérialisation.
- Pas de champ supplémentaire.

Le vecteur STARTED publié dans MRI-004.17 est un vecteur minimal historique sans `window_id` et `expected_sources`. Il reste un vecteur de hash de référence, mais il n'est pas un exemple complet du payload STARTED final. Un nouveau vecteur STARTED complet doit être ajouté.

### 2.5 Payload SOURCE_RESULT exact

Champs racine : `window_id`, `source_id`, `outcome`.

- `window_id` doit être égal au window_id du STARTED.
- `source_id` doit appartenir à expected_sources.
- Une seule preuve SOURCE_RESULT par source attendue et par tentative, sauf évolution explicite du schéma.
- `outcome` appartient à `OBSERVED`, `NO_REACTION_OBSERVED`, `SOURCE_FAILED`, `NOT_SCHEDULED`, `UNKNOWN`.
- Le contenu fournisseur, texte libre, message d'exception, prix, compte et donnée personnelle sont interdits.

La séquence SOURCE_RESULT est allouée par le writer de la tentative. Un retry réutilise strictement l'événement déjà alloué ; il ne crée pas une seconde preuve.

### 2.6 Payload FINISHED exact

Champs racine : `run_status`.

Valeurs : `OK`, `PARTIAL`, `EMPTY`, `FAILED`.

Aucun compteur ni détail d'exception dans cette première version du validateur. Toute extension devra être ajoutée explicitement au schéma et à ses vecteurs.

### 2.7 Cycle de vie et règles inter-événements

- STARTED exactement sequence 0, précédent null.
- SOURCE_RESULT : sequence 1..N, contiguë.
- FINISHED : sequence N+1, terminal.
- FINISHED peut suivre directement STARTED si N=0.
- Pas de SOURCE_RESULT pour une source non attendue.
- Pas de doublon source.
- Pas de FINISHED multiple.
- Pas d'événement après FINISHED.
- Chaque événement porte le run_id et attempt identiques au reste de la chaîne.
- previous_event_hash doit égaler le hash recalculé de l'événement précédent.
- Les timestamps sont non décroissants.
- Un fork, trou, doublon contradictoire ou hash incorrect invalide la chaîne.

## 3. API pure envisagée

Fichier proposé : `intelligence/event_v2.py`.

Fonctions pures envisagées :
- `canonical_json_bytes(value) -> bytes`
- `parse_canonical_event(raw_bytes) -> dict`
- `compute_run_key(run_id) -> str`
- `compute_event_id(run_id, attempt, sequence, event_type) -> str`
- `compute_event_hash(event_without_hash) -> str`
- `event_storage_path(event) -> str`
- `validate_event(event) -> ValidatedEvent`
- `validate_event_chain(events) -> ChainValidation`

Les erreurs doivent être des catégories stables et sûres, sans recopier le contenu brut de l'événement dans les messages :
- `INVALID_ENCODING`
- `INVALID_JSON`
- `DUPLICATE_KEY`
- `NON_CANONICAL_JSON`
- `INVALID_SCHEMA`
- `INVALID_IDENTIFIER`
- `INVALID_TIMESTAMP`
- `INVALID_EVENT_ID`
- `INVALID_EVENT_HASH`
- `INVALID_PATH`
- `INVALID_SEQUENCE`
- `INVALID_PREVIOUS_HASH`
- `UNEXPECTED_SOURCE`
- `DUPLICATE_SOURCE_RESULT`
- `EVENT_AFTER_FINISHED`
- `INVALID_LIFECYCLE`

Aucun effet de bord, horloge système, réseau, filesystem ou état global ne doit être utilisé dans ces fonctions.

## 4. Matrice de tests unitaires

### 4.1 Canonicalisation
- objet valide produit exactement les octets attendus ;
- ordre de clés différent dans l'entrée non canonique rejeté par parseur strict ;
- espaces superflus rejetés ;
- saut de ligne final rejeté ;
- BOM rejeté ;
- UTF-8 invalide rejeté ;
- clé JSON dupliquée rejetée ;
- caractère non ASCII rejeté ;
- float, NaN, Infinity et notation exponentielle rejetés ;
- booléen dans un champ entier rejeté.

### 4.2 Schéma
- schema_version 2 accepté ;
- schema_version 1, 3, chaîne et booléen rejetés ;
- champ obligatoire manquant rejeté ;
- champ supplémentaire rejeté ;
- type incorrect rejeté ;
- identifiant vide, trop long, espace, slash ou caractère de contrôle rejeté ;
- attempt 0, négatif, float, booléen et dépassement rejetés ;
- sequence négative, float, booléen et dépassement rejetés.

### 4.3 Timestamps
- timestamp UTC canonique valide accepté ;
- date calendrier impossible rejetée ;
- timestamp sans microsecondes rejeté ;
- précision 3 ou 7 chiffres rejetée ;
- offset +01:00 rejeté ;
- timestamp sans Z rejeté ;
- heure hors plage rejetée ;
- timestamp non décroissant accepté ;
- timestamp décroissant rejeté au niveau chaîne.

### 4.4 Identité, hash et chemin
- vecteur run_key positif ;
- vecteur event_id positif ;
- vecteur event_hash positif ;
- un octet modifié change le hash ;
- champ modifié sans recalcul du hash rejeté ;
- event_id d'une autre séquence rejeté ;
- mauvais run_key rejeté ;
- mauvais chemin, mauvais attempt ou mauvaise séquence rejetés ;
- hash hex majuscule, longueur incorrecte ou caractère invalide rejeté.

### 4.5 Payloads
- STARTED manuel exact accepté ;
- STARTED schedule exact accepté ;
- schedule sans scheduled_at, window_id ou expected_sources rejeté ;
- manual avec scheduled_at ou expected_sources rejeté ;
- expected_sources vide, doublonné ou non trié rejeté ;
- SOURCE_RESULT pour source attendue accepté ;
- SOURCE_RESULT source inconnue rejeté ;
- SOURCE_RESULT window_id différent rejeté ;
- outcome inconnu rejeté ;
- FINISHED avec chaque run_status autorisé accepté ;
- FINISHED avec statut inconnu ou champ supplémentaire rejeté.

### 4.6 Chaîne
- STARTED seul valide comme tentative inachevée ;
- STARTED + FINISHED valide ;
- STARTED + un ou plusieurs SOURCE_RESULT + FINISHED valide ;
- STARTED absent rejeté ;
- STARTED sequence non nulle rejeté ;
- séquence manquante ou dupliquée rejetée ;
- previous_event_hash incorrect rejeté ;
- fork à même séquence rejeté ;
- source attendue absente : chaîne structurelle valide mais résultat métier incomplet ;
- source dupliquée rejetée ;
- FINISHED non terminal rejeté ;
- deux FINISHED rejetés ;
- événement après FINISHED rejeté ;
- run_id/attempt mélangés rejetés ;
- timestamps décroissants rejetés.

## 5. Vecteurs cryptographiques à publier

Les vecteurs existants à conserver :
- STARTED minimal de MRI-004.17 : event_id `bb1d229746609f259481e8685f82a9b19b274daf38a6e05f9b189e34de66a416`, event_hash `a41cb5fb52e4bc3f079090647e02e204f8a1b4c9e84fa8f79bd5d57f48dd8d90`.
- run_key recalculé pour `run-demo` : `9b040e473d10a66e79a716c4ff6f35bd543d18358c1017c3421b4f2d6c96afd3`.

Ajouter avant implémentation :
- STARTED scheduled complet ;
- STARTED manual complet ;
- SOURCE_RESULT lié au STARTED ;
- FINISHED terminal lié à SOURCE_RESULT ;
- chemin exact pour chaque événement ;
- un vecteur invalide dont un seul champ a été modifié ;
- timestamp offset et timestamp non canonique rejetés.

Chaque vecteur doit inclure input JSON, octets canoniques, event_id, previous_event_hash, event_hash et chemin attendu. Vérifier par deux implémentations indépendantes, par exemple Python et une implémentation JavaScript/Node exécutée localement par un mainteneur ; ne pas prétendre à cette vérification croisée avant résultat observé.

## 6. Critères de sortie 004.18-A

La phase A est prête à être considérée terminée seulement si :
1. les contrats de payload et identifiants sont figés ;
2. les vecteurs positifs et négatifs sont publiés ;
3. le validateur pur est implémenté ;
4. tous les tests unitaires ciblés passent ;
5. la suite offline complète passe ;
6. les vecteurs sont confirmés par une seconde implémentation indépendante ;
7. aucun secret, réseau, appel fournisseur ou effet de bord n'est introduit.

La validation d'un événement individuel ne prouve pas que la chaîne est complète, que le dépôt est durable ou que l'historique Git est exhaustif. Ces preuves appartiennent aux étapes suivantes.

## 7. Limites et état

- Ce document est un plan technique, pas une implémentation.
- Aucun code v2 n'a été intégré dans ce travail.
- Aucun test v2 n'a été exécuté.
- Les vecteurs STARTED existants ont été recalculés indépendamment en Python et concordent.
- Le vecteur run_key a été calculé ; il reste à le faire confirmer par une seconde implémentation.
- Le commit code testé connu reste `d8855adc44332a9a5053dd0a02b26b1686f63d7d`, CI `41694975268` (509 tests, 508 passés, 1 ignoré).
- Le code GitHub n'est pas modifié par ce plan.
- Aucun scheduler, backend privé, secret, appel fournisseur ou dépense n'est activé.


## 8. Vérification croisée des vecteurs de base — 4 novembre 2026

Les vecteurs `run-demo` ont été recalculés par deux implémentations indépendantes :
- Python : `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)` puis SHA-256 avec les préfixes normatifs.
- JavaScript : sérialiseur récursif indépendant à clés triées, puis SHA-256 via le module crypto standard.

Résultats identiques dans les deux implémentations :
- run_key : `9b040e473d10a66e79a716c4ff6f35bd543d18358c1017c3421b4f2d6c96afd3`
- event_id : `bb1d229746609f259481e8685f82a9b19b274daf38a6e05f9b189e34de66a416`
- event_hash : `a41cb5fb52e4bc3f079090647e02e204f8a1b4c9e84fa8f79bd5d57f48dd8d90`
- canonical JSON : octets ASCII strictement identiques.

Cette vérification croisée confirme les formules et le vecteur minimal STARTED. Elle ne constitue pas encore un validateur implémenté, ni une suite de tests du dépôt. Les vecteurs de payloads complets STARTED/SOURCE_RESULT/FINISHED restent à construire et à vérifier.
