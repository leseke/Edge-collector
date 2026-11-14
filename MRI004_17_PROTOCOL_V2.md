# MRI-004.17 — Protocole durable v2 (document de référence)

Statut : **spécification de conception — non implémentée**  
Branche cible : `edge/mri-004-continuity-notification-contract`  
Périmètre : identité des événements, chaîne append-only, transport, retries, restauration, preuve d'historique et publication de confiance.

Ce document consolide MRI-004.17-A à G. Il prévaut sur les propositions intermédiaires incompatibles de MRI-004.16 pour toute future implémentation v2. Il ne transforme pas le backend GitHub privé en service opérationnel.

---

## 1. Décisions normatives

1. Les fichiers d'événements immuables sont l'unique source de vérité.
2. Un manifeste éventuel est un cache reconstructible ; il ne peut ni créer ni supprimer une preuve.
3. Une chaîne est ordonnée par `(run_id, attempt, sequence)`. Il n'existe pas d'ordre global entre runs distincts.
4. Le stockage est create-only. Un objet existant n'est jamais écrasé.
5. Les retries réutilisent exactement le même chemin et les mêmes octets canoniques.
6. Une réponse ambiguë déclenche une lecture de vérification, jamais une nouvelle séquence.
7. Un historique final valide ne suffit pas : la complétude de l'inventaire et l'absence de réécriture historique doivent également être prouvées.
8. Une preuve insuffisante entraîne `DEGRADED` ou `UNKNOWN`, jamais une continuité vérifiée.
9. v1 peut être lu en mode compatibilité, mais ne peut pas atteindre `CONTINUITY_VERIFIED`. v2 est le seul format d'écriture futur.
10. Aucune donnée financière personnelle, donnée de compte, secret, URL privée, PII, offre détaillée ou payload brut fournisseur n'est admise dans ce journal.

## 2. Encodage canonique

### 2.1 JSON canonique

Les événements sont encodés en UTF-8 strict, sans BOM, sans saut de ligne final. La sérialisation canonique est :

- clés d'objets triées lexicographiquement ;
- séparateurs compacts `,` et `:` ;
- caractères Unicode émis directement en UTF-8 ;
- aucun NaN, Infinity, nombre non fini, clé dupliquée ou type non JSON ;
- les booléens ne sont jamais acceptés à la place d'entiers ;
- aucune normalisation silencieuse avant validation.

La validation doit parser le JSON avec détection des clés dupliquées, puis re-sérialiser et comparer les octets obtenus aux octets d'origine. Toute différence est rejetée.

### 2.2 Horodatage

`occurred_at_utc` doit respecter exactement :

`YYYY-MM-DDTHH:MM:SS.ffffffZ`

UTC, suffixe `Z`, six chiffres de microsecondes obligatoires. Les timestamps naïfs et offsets tels que `+01:00` sont rejetés. Aucune conversion silencieuse n'est autorisée.

`scheduled_at` reste un champ métier distinct : le contexte de planification peut accepter un offset équivalent puis normaliser vers UTC avant la création de l'événement. La valeur stockée dans l'événement doit ensuite être canonique.

## 3. Identité et chemin

### 3.1 Identifiants

- `run_id` : identifiant opaque non vide fourni par l'orchestrateur.
- `attempt` : entier strictement positif.
- `sequence` : entier strictement positif ou nul, sans booléen.
- `run_key` : SHA-256 de `b"EDGE-MRI-RUN-V2\\n" + canonical_json(run_id)`.
- `event_id` : SHA-256 de `b"EDGE-MRI-EVENT-ID-V2\\n" + canonical_json([run_id, attempt, sequence, event_type])`.

La canonicalisation utilisée dans ces formules est celle de la section 2.1. L'identifiant est stable pour une même identité logique. Un même emplacement revendiqué avec un contenu différent est un conflit d'intégrité, pas une mise à jour.

### 3.2 Chemin

`runs/<run_key>/<attempt>/<sequence>.json`

Le chemin est calculé localement à partir des champs validés. Il n'est jamais accepté comme donnée arbitraire venant du contenu. Le chemin doit correspondre exactement aux valeurs de l'événement.

Cette structure remplace `events/YYYY/MM/DD/<event_id>.json` proposé en MRI-004.16. Le classement par date ne prouvait pas l'ordre d'une chaîne et rendait les collisions de séquence moins visibles.

## 4. Schéma d'événement v2

Champs obligatoires au niveau racine :

| Champ | Type / contrainte |
|---|---|
| `schema_version` | entier strict égal à 2 |
| `event_id` | SHA-256 hexadécimal minuscule |
| `run_id` | chaîne non vide |
| `attempt` | entier strict >= 1 |
| `sequence` | entier strict >= 0 |
| `previous_event_hash` | null uniquement au STARTED, sinon SHA-256 hexadécimal |
| `occurred_at_utc` | timestamp canonique UTC |
| `event_type` | STARTED, SOURCE_RESULT ou FINISHED |
| `payload` | objet conforme à l'allowlist du type |
| `event_hash` | SHA-256 hexadécimal minuscule |

Aucun champ supplémentaire n'est autorisé.

### 4.1 Cycle d'une tentative

- STARTED : exactement `sequence = 0`, `previous_event_hash = null`.
- SOURCE_RESULT : séquences contiguës de 1 à N, chacune liée au hash de l'événement précédent.
- FINISHED : exactement la séquence N+1, terminale.
- Aucun événement n'est admis après FINISHED.
- Un run sans résultat de source a STARTED à 0 puis FINISHED à 1.
- Une tentative non terminée peut être conservée comme incomplète, mais ne devient pas une tentative réussie.

Une seule identité d'écrivain logique peut allouer la séquence d'une tentative. Deux workers ne doivent jamais écrire simultanément dans la même chaîne sans mécanisme externe de claim/coordination. Les runs distincts peuvent être écrits en parallèle.

### 4.2 Payloads autorisés

STARTED :
- `trigger` : chaîne allowlistée, non vide ;
- `scheduled_at` : timestamp UTC canonique ou null selon le trigger ;
- `window_id` : chaîne opaque ou null ;
- `expected_sources` : liste dédupliquée d'identifiants de sources allowlistés.

SOURCE_RESULT :
- `window_id` ;
- `source_id` ;
- `outcome` : OBSERVED, NO_REACTION_OBSERVED, SOURCE_FAILED, NOT_SCHEDULED ou UNKNOWN ;
- champs minimaux de statut autorisés uniquement, jamais de payload fournisseur, de détail d'offre ou d'exception brute.

FINISHED :
- `run_status` : OK, PARTIAL, EMPTY ou FAILED ;
- métadonnées minimales explicitement allowlistées.

Les schémas précis doivent être codés comme validateurs dédiés. Les dictionnaires libres ne sont pas autorisés.

## 5. Hash cryptographique

### 5.1 Hash d'événement

`event_hash = SHA256(b"EDGE-MRI-EVENT-V2\\n" + canonical_json(event_without_event_hash))`

Le champ `event_hash` est exclu du document hashé. `previous_event_hash` est inclus : la chaîne est donc liée cryptographiquement.

### 5.2 Vérification de chaîne

Pour chaque `(run_id, attempt)` :
1. une seule séquence 0 STARTED ;
2. séquences strictement contiguës ;
3. event_id recalculé et identique ;
4. previous_event_hash égal au hash recalculé de l'événement précédent ;
5. event_hash recalculé et identique ;
6. un seul FINISHED terminal au maximum ;
7. timestamps monotones selon l'ordre de séquence ;
8. aucun doublon, fork, trou ou événement postérieur à FINISHED.

Ne jamais trier des événements par timestamp pour réparer un ordre manquant. Le tri par séquence sert uniquement à vérifier les clés déjà présentes ; il ne remplace pas la preuve de contiguïté ni la chaîne de hash.

## 6. Contrat de transport create-only

Résultats normalisés :
- `COMMITTED` : création confirmée ;
- `ALREADY_COMMITTED` : chemin existant et octets canoniques strictement identiques ;
- `UNCONFIRMED` : résultat impossible à établir après lecture de vérification ;
- `CONFLICT` : chemin existant avec contenu différent.

Comportement :
- création conditionnelle uniquement ;
- si chemin déjà présent, lire et comparer les octets exacts ;
- même contenu : succès idempotent ;
- contenu différent : ne jamais écraser, signaler conflit/fork et mettre la chaîne en quarantaine ;
- réponse perdue après écriture : readback du même chemin ;
- backend inaccessible : aucune preuve de persistance ;
- ne jamais attribuer une nouvelle séquence lors d'un retry.

Politique de retry initiale proposée : maximum 3 tentatives, backoff 1 s puis 2 s, plafond 4 s. Pas de retry sur CONFLICT, erreur de validation ou refus de permission. Après une réponse ambiguë, effectuer un readback avant toute nouvelle tentative. Ces valeurs restent configurables et devront être confirmées par tests ; elles ne justifient pas un appel externe automatique dans la présente étape.

## 7. Restauration déterministe

### 7.1 Snapshot épinglé

1. Lire la référence de branche une seule fois.
2. Capturer le SHA du commit.
3. Toutes les lectures d'arbre, blobs et commits sont effectuées relativement à ce SHA.
4. Si une lecture ne peut pas être épinglée à ce SHA, la restauration est dégradée.
5. Un HEAD qui avance pendant la restauration ne change pas le snapshot.

### 7.2 Inventaire

- parcourir l'arbre du commit épinglé ;
- si l'arbre récursif est tronqué, parcourir tous les sous-arbres concernés ;
- traiter la pagination jusqu'à preuve de fin ;
- refuser toute réponse partielle, permission manquante ou objet inaccessible comme preuve d'inventaire complet ;
- ne pas inférer l'absence d'un événement à partir d'un inventaire incomplet.

### 7.3 Vérification des blobs

Pour chaque blob :
- vérifier type, chemin, taille, encodage et contenu ;
- recalculer le SHA Git blob : SHA-1 de `b"blob " + ascii(len(content)) + b"\\0" + content` ;
- vérifier l'égalité avec le blob SHA annoncé par Git ;
- parser le JSON strict, refuser BOM et clés dupliquées ;
- vérifier l'égalité octet à octet avec le JSON canonique ;
- valider schéma, identité, chemin et hash d'événement.

Le SHA-1 du blob Git sert à vérifier l'identité de l'objet Git ; il ne remplace pas le SHA-256 de l'événement.

### 7.4 Reconstruction

Grouper par `run_id, attempt`, puis vérifier chaque chaîne. Aucun résultat ne peut être reconstruit depuis un événement isolé dont la chaîne est invalide. Les événements positifs isolément vérifiables peuvent être conservés comme données diagnostiques internes, mais pas comme preuve de continuité globale.

## 8. Preuve d'intégrité de l'historique Git

Un arbre final complet ne prouve pas qu'aucun fichier n'a été supprimé puis recréé auparavant.

Une restauration peut annoncer `HISTORY_VALID` uniquement si :
- un commit de genèse de confiance est fourni par une ancre conservée indépendamment du dépôt ;
- le commit épinglé descend de cette ancre ;
- tous les commits intermédiaires nécessaires sont accessibles ;
- la chaîne des parents est vérifiée ;
- seuls des ajouts de fichiers d'événements conformes sont autorisés ;
- aucune modification, suppression, renommage, merge ou altération de structure n'est détectée.

Le protocole initial refuse les commits de merge afin de conserver une histoire linéaire et vérifiable. Des runs distincts peuvent être concurrents au niveau applicatif, mais le writer Git doit sérialiser les commits. Un commit de merge ne constitue pas un mécanisme de résolution acceptable pour une même chaîne.

Si l'API ne fournit pas tous les commits ou arbres nécessaires, `HISTORY_VALID = UNKNOWN`. Une branche protégée, des permissions restreintes et une identité dédiée sont des contrôles complémentaires, pas une preuve cryptographique suffisante.

La perte du dépôt, sa recréation, un changement de genèse ou une réécriture d'historique entraîne le rejet de la preuve historique.

## 9. Statuts de confiance et publication

Dimensions indépendantes :

| Dimension | Valeurs |
|---|---|
| Restauration | RESTORE_COMPLETE / RESTORE_DEGRADED / RESTORE_REJECTED |
| Événements | EVENTS_VALID / EVENTS_INVALID / EVENTS_UNKNOWN |
| Historique | HISTORY_VALID / HISTORY_INVALID / HISTORY_UNKNOWN |
| Continuité | CONTINUITY_VERIFIED / CONTINUITY_DEGRADED / CONTINUITY_UNKNOWN |

Conditions :
- CONTINUITY_VERIFIED exige RESTORE_COMPLETE + EVENTS_VALID + HISTORY_VALID + contrôles de reconstruction conformes.
- Une dimension INVALID interdit la continuité vérifiée.
- Une dimension UNKNOWN ou DEGRADED masque les ratios globaux.
- Un snapshot complet prouve seulement l'état de ce snapshot ; sans audit historique depuis l'ancre de confiance, il ne prouve pas l'absence de suppressions antérieures.
- Un SOURCE_FAILED correctement enregistré prouve qu'un contrôle a échoué et que cet échec a été journalisé ; il ne prouve pas une absence de réaction du marché.
- Heartbeat, run terminé et source contrôlée sont trois notions distinctes.

## 10. Vecteur de référence cryptographique

Vecteur STARTED déterministe :

```json
{
  "schema_version": 2,
  "event_id": "bb1d229746609f259481e8685f82a9b19b274daf38a6e05f9b189e34de66a416",
  "run_id": "run-demo",
  "attempt": 1,
  "sequence": 0,
  "previous_event_hash": null,
  "occurred_at_utc": "2026-11-03T01:00:00.000000Z",
  "event_type": "STARTED",
  "payload": {
    "scheduled_at": "2026-11-03T01:00:00.000000Z",
    "trigger": "schedule"
  },
  "event_hash": "a41cb5fb52e4bc3f079090647e02e204f8a1b4c9e84fa8f79bd5d57f48dd8d90"
}
```

Canonical JSON utilisé pour calculer event_hash (sans le champ event_hash) :

```text
{"attempt":1,"event_id":"bb1d229746609f259481e8685f82a9b19b274daf38a6e05f9b189e34de66a416","event_type":"STARTED","occurred_at_utc":"2026-11-03T01:00:00.000000Z","payload":{"scheduled_at":"2026-11-03T01:00:00.000000Z","trigger":"schedule"},"previous_event_hash":null,"run_id":"run-demo","schema_version":2,"sequence":0}
```

Formules du vecteur :
- event_id = SHA256(`b"EDGE-MRI-EVENT-ID-V2\\n" + canonical_json(["run-demo", 1, 0, "STARTED"])`)
- event_hash = SHA256(`b"EDGE-MRI-EVENT-V2\\n" + canonical_json(event sans event_hash)`)

Ce vecteur couvre uniquement STARTED. Avant implémentation, ajouter des vecteurs indépendants pour SOURCE_RESULT, FINISHED, run_key, chemin, timestamps invalides, forks et réponses ambiguës. Le calcul des vecteurs doit être reproduit par deux implémentations indépendantes ou vérifié par un outil cryptographique standard ; aucune valeur générée à la main ne doit être acceptée.

## 11. Matrice minimale des tests d'acceptation

### Validateur et canonicalisation
- schema_version booléen, entier incorrect, champ supplémentaire ;
- clés dupliquées, BOM, UTF-8 invalide, JSON non canonique ;
- timestamp naïf, offset non UTC, précision incorrecte ;
- event_id et event_hash corrects/incorrects ;
- path/run_key/attempt/sequence incohérents.

### Chaîne
- STARTED absent ou dupliqué ;
- séquence manquante, dupliquée ou réordonnée ;
- previous hash incorrect ;
- fork concurrent à même séquence ;
- SOURCE_RESULT après FINISHED ;
- FINISHED multiple ou non terminal ;
- timestamp non monotone.

### Transport
- create-only, idempotence exacte, conflit de contenu ;
- réponse perdue avant/après écriture ;
- readback positif/négatif ;
- backend indisponible ;
- retries bornés ;
- deux runs concurrents et deux writers concurrents sur le même run.

### Restauration et historique
- snapshot épinglé malgré HEAD mouvant ;
- pagination complète/incomplète ;
- arbre récursif tronqué avec parcours des sous-arbres ;
- blob SHA invalide, blob inaccessible, type incorrect ;
- commit manquant, parent incorrect, merge ;
- suppression, modification, renommage, ajout autorisé ;
- genèse inconnue ou modifiée ;
- historique inaccessible et inventaire partiel.

### Publication
- seuls les quatre niveaux de confiance conformes donnent VERIFIED ;
- ratios absents pour UNKNOWN/DEGRADED ;
- événements individuels valides conservés sans prétendre à la continuité ;
- SOURCE_FAILED jamais assimilé à NO_REACTION_OBSERVED.

## 12. Plan d'implémentation proposé

Ordre recommandé :
1. 004.17-A : module de canonicalisation, schéma strict, identités et hashes ;
2. 004.17-B : chaîne séquencée, vérification, forks ;
3. 004.17-C/D : transport simulé puis interface create-only et retries ;
4. 004.17-E : restauration épinglée et inventaire complet ;
5. 004.17-F : audit de l'historique Git depuis l'ancre ;
6. 004.17-G : rapport de confiance et règles de publication ;
7. tests offline complets, puis revue de sécurité ;
8. seulement après provisionnement manuel d'un dépôt privé distinct et de credentials restreints, étude d'un test d'intégration explicitement autorisé.

Aucun scheduler, collecteur live, connecteur externe, notification, dépense API ou secret n'est activé par ce protocole.

## 13. État opérationnel au moment de la rédaction

- Spécification MRI-004.17-A à G : consolidée dans ce document.
- Code v2 : non intégré.
- Tests v2 : non exécutés.
- Backend GitHub privé : non provisionné.
- Scheduler réel : absent.
- SQLite runner-local : non durable entre exécutions.
- CI existante : 509 tests, 508 passés, 1 ignoré, 0 échec sur le dernier commit de code testé connu (d8855adc44332a9a5053dd0a02b26b1686f63d7d ; run 41694975268). Les commits ultérieurs mentionnés dans le statut de branche sont documentaires uniquement.
- Branche de travail : `edge/mri-004-continuity-notification-contract`.
- Branche `main` : ne pas modifier, fusionner ou rebaser sans autorisation explicite.

**Règle de reporting :** ne jamais présenter une spécification comme une implémentation, un test prévu comme un test exécuté, un journal local comme une persistance durable, ni un inventaire de snapshot comme une preuve d'exhaustivité historique.
