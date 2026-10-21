# EDGE Intelligence Report v1 — AI-001

Standard de rapports d'analyse de marché, prêt à accueillir un futur agent IA. **Aucun agent actif, aucun appel OpenAI, aucune dépense, aucune modification des collecteurs ni du moteur d'allocation.**

## 1. Architecture
```
intelligence/
  schema/edge_intelligence_report.v1.schema.json   schéma formel (JSON Schema 2020-12)
  validator.py      interprète CE schéma (pas de dépendance) + règles sémantiques EDGE ; calcule le niveau de vérification
  store.py          publication immuable dans data/intelligence/ (versions chaînées par SHA-256)
  charts.py         vues graphiques dérivées uniquement des points du rapport
  agent_contract.py contrat de l'agent futur (entrée, sortie, ingestion, verrou de dépense R4.2)
  examples/         exemple Pokémon Chine 100 % fictif (v1 + v2 corrigée) et son générateur
data/intelligence/  (créé à la première publication ; absent dans ce lot)
  index.json, reports/<report_id>/v0001.json …
```
Flux : collecteurs / humain / agent → `ingest_agent_output` (brouillon) → `assess` → `ReportStore.publish` → dashboard (lecture seule).

## 2. Schéma — champs obligatoires (racine)
| Champ | Type | Règles |
|---|---|---|
| `schema` | const `edge.intelligence_report` | |
| `schema_version` | `1.x.y` | |
| `report_id` | `eir_[a-z0-9][a-z0-9_.-]{1,63}` | stable entre versions |
| `report_version` | entier ≥ 1 | v1 ne remplace rien ; vN remplace vN-1 |
| `supersedes` | objet ou null | obligatoire si version > 1 : id, version N-1, SHA-256 de N-1 |
| `created_at`, `data_as_of` | ISO 8601 **avec fuseau** | `data_as_of` ≤ `created_at` |
| `production_status` | `draft` `partial` `complete` `retracted` | `complete` : non simulé, tous les faits vérifiés, décision du moteur EDGE, ≥ 1 source |
| `simulated` | booléen | obligatoirement `true` si un seul élément est simulé |
| `subject` | title, market, category (`tcg` `toys` `video_games` `collectibles` `other`), region (ISO 3166 alpha-2, `EU`, `GLOBAL`) | facultatifs : language, tags |
| `sources[]` | source_id `src_…`, title, publisher, url (https ou null), published_at (date ou null), accessed_at (date), tier (`primary` `secondary` `unverified`), simulated | published ≤ accessed ≤ created ; source réelle sans URL ⇒ `unverified` |
| `claims[]` | claim_id `clm_…`, kind (`fact` `hypothesis` `uncertainty` `limitation` `invalidated`), statement, verification (`verified` `unverified` `contradicted` `simulated`), source_ids, author (`human` `agent` `edge_engine` `collector`), confidence | voir §3 |
| `datasets[]` | dataset_id `ds_…`, title, unit (`currency` `count` `percent` `index` `units`), currency (ISO 4217 ou null), measure, territory, period {start,end}, frequency, provenance {source_ids, method, collected_by}, simulated, points[{t, value, status}] | voir §3 |
| `charts[]` | chart_id `cht_…`, type (`line` `bar`), title, dataset_ids | même unité et même devise par graphique |
| `economics` | listed_price_dataset_ids, realized_sale_dataset_ids, availability {buyable_verified, evidence_claim_ids}, fees {claim_ids, verified}, liquidity {claim_ids}, roi_hypotheses[{scenario, net_roi_pct, assumption_claim_ids (≥1), is_hypothesis = true}], supply_demand_claim_ids | prix affichés et ventes réalisées jamais confondus |
| `decisions` | agent_opinion {stance, rationale, claim_ids, is_decision = false} ou null ; edge_decision {decision, decided_by (`edge_engine` `none`), rules_applied, evidence_refs, decided_at, engine_version?} | voir §3 |
| `history` | previous_versions[{report_version, content_sha256}], related_report_ids, changes[{path, reason, before?, after?}], corrections[{correction_id, target, description, reason, corrected_at}], conclusion_changes[{from, to, reason}] | |
Facultatif : `freshness.max_data_age_days`. Tout champ non prévu est **refusé** (objets fermés).

## 3. Règles sémantiques (validator.py)
- **Nombres** : finis (NaN/Infinity refusés), jamais booléens ni textes ; prix, volumes et unités ≥ 0 ; pourcentage ≥ -100.
- **Points** : dates dans la période, strictement croissantes, ≤ `data_as_of` ; `value = null` ⇔ `status = missing` + `missing_reason`.
- **Unités/devises** : `unit = currency` ⇔ devise ISO 4217 reconnue ; une mesure de prix exige une unité monétaire.
- **Provenance** : un fait `verified` exige ≥ 1 source réelle `primary`/`secondary` ; seuls les faits peuvent être `verified` ; une affirmation citant une source simulée est `simulated` ; une mesure exige une provenance.
- **Simulation** : un dataset simulé ne contient aucune mesure ; un dataset réel aucun point simulé ; un rapport contenant un élément simulé se déclare simulé et ne peut être `complete`.
- **Politique EDGE** : aucune clé d'allocation ni donnée financière privée (`allocation`, `treasury`, `engaged`, `capital`, `budget`…) **n'importe où** dans un rapport ; `decided_by = none` ⇒ `NOT_EVALUATED` ; BUY/STRONG_BUY exige le moteur EDGE, ses règles, ses preuves, une achetabilité vérifiée, des ventes réalisées, et un rapport non simulé. L'avis de l'agent n'est jamais une décision (`is_decision = false`, aucun BUY possible dans `stance`).
- **Versionnement** : vN cite vN-1 et son empreinte ; une nouvelle version motive ses changements ou corrections ; un retrait motive son changement de conclusion.

**Niveau de vérification — calculé, jamais déclaré** : `invalid` · `retracted` · `simulated` · `draft` · `partially_verified` · `fully_verified` (seulement `complete`, non simulé, données fraîches, aucune contradiction non résolue). Un rapport incomplet peut être publié comme brouillon ou partiel, jamais comme vérifié.

## 4. Compatibilité et versionnement du schéma
- **Mineure (1.x)** : ajouts facultatifs uniquement ; un rapport 1.0 reste valide.
- **Majeure (2.0)** : tout changement de champ obligatoire, de type ou de sens ; nouveau fichier de schéma, ancien validateur conservé.
- Les consommateurs existants ne changent pas : `radar.json`, `data/discovery/latest.json`, `data/searchlab/` ne sont pas modifiés ; le dashboard ajoute une section distincte qui ne s'affiche que si `data/intelligence/index.json` existe.

## 5. Lecture et affichage par le dashboard
1. Lire `data/intelligence/index.json` ; afficher la dernière version de chaque `report_id` avec son `verification_level` (badge) et la mention SIMULÉ.
2. Ouvrir `reports/<id>/vNNNN.json` (chemin validé par motif, aucun chemin libre).
3. Afficher **toujours** le `label` du niveau de vérification en tête.
4. Graphiques : uniquement les points du rapport ; donnée manquante = **trou** (jamais interpolée) ; estimation = pointillés ; dataset simulé = filigrane « DONNÉES SIMULÉES ».
5. Affirmations groupées par nature, avec statut, auteur et sources.
6. Avis de l'agent et **décision EDGE dans deux blocs séparés** ; aucun montant d'allocation (privé, jamais dans un rapport).
7. Historique : corrections et changements de conclusion visibles.
Tout texte est échappé (titres et affirmations peuvent provenir de sources externes ou d'une IA).

## 6. Contrat de l'agent futur
- Entrée (`build_agent_input`) : sujet, sources, métadonnées des datasets **sans valeurs**, décision EDGE.
- Sortie autorisée : `claims` (sans chiffres structurés, sources existantes uniquement), `agent_opinion` (stance, rationale, claim_ids), `chart_requests` (identifiants de datasets uniquement), `notes`.
- Refusé : datasets, valeurs, prix, montants, allocations, décisions, verification `verified`, sources inventées.
- Ingestion ⇒ rapport `draft`, affirmations `unverified` (ou `simulated`).
- `run_agent` : un fournisseur payant passe obligatoirement par `PaidGate` + `SpendGuard` (R4.2 : une réservation par appel, requête approuvée, plafonds).

## 7. Commandes reproductibles
```
python -m unittest discover -s tests                 # suite complète
python -m tools.run_tests_offline                    # suite complète, réseau coupé
python -m unittest tests.test_intelligence -v        # lot AI-001
python -m intelligence.examples.build_examples       # régénère et valide les exemples
python -m tools.check_public_files --tracked         # aucune fuite
```

## 8. Risques et limites
- Les exemples sont **fictifs** : aucune valeur du marché chinois n'a été vérifiée dans ce lot.
- Le validateur contrôle la cohérence, pas la véracité : une source réelle mal citée reste une erreur humaine possible (d'où `verified` réservé aux humains et collecteurs).
- Liste ISO 4217 restreinte (12 devises) : extension par version mineure.
- Le filtre de clés privées est volontairement large (ex. un champ nommé `capital` est refusé même s'il est anodin).
- Immutabilité garantie par l'outil et vérifiable par empreinte, pas contre une modification manuelle du dépôt (détectée par `verify()`, pas empêchée).
- Affichage testé en navigateur simulé (jsdom), pas sur un vrai téléphone.

## 9. Retour arrière
Lot isolé : deux commits (`fix(replay)` séparé, puis `feat(ai-001)`).
- Annuler AI-001 seul : `git revert <commit ai-001>` — supprime `intelligence/`, les tests, la doc et la section du dashboard ; aucune donnée publiée à migrer (`data/intelligence/` n'existe pas encore).
- Le correctif `fix(replay)` est indépendant et peut être conservé.
- Si des rapports avaient été publiés : supprimer `data/intelligence/` suffit, aucun autre fichier n'en dépend.

## 10. Proposition pour AI-002 (non implémentée)
1. **Agent hors ligne d'abord** : fournisseur « rejeu » qui lit une sortie d'agent enregistrée, pour tester l'ingestion de bout en bout sans modèle.
2. **Fournisseur réel derrière le verrou R4.2** : `paid = True`, coût estimé par appel déclaré au registre, autorisation et plafonds dans `config.private.json`, journal réservation/tentative/résultat ; sortie JSON stricte refusée si non conforme (aucune réparation silencieuse).
3. **Vérification humaine** : outil de promotion `unverified → verified` produisant une nouvelle version avec correction motivée.
4. **Liaison au moteur** : `edge_decision` rempli automatiquement depuis la sortie privée du moteur (sans montants).
5. **Évaluation** : rapprocher les avis d'agent des résultats observés (`discovery/outcomes.py`), sans jamais en faire une règle d'achat.

---
# AI-001.1 — Durcissement (fraîcheur, intégrité, vérification, dépenses)
Schéma **1.1.0** (ajout facultatif uniquement) : tout rapport 1.0.0 reste valide.

## A. Fiabilité ≠ actualité
- `verification_level` = **fiabilité à la rédaction** (inchangée dans le temps).
- `assess(report, now)["timeliness"]` = **actualité à la consultation** : `current` · `stale` · `unknown` (consultation antérieure aux données, date illisible).
- Sans `freshness.max_data_age_days` : **politique par défaut de 30 jours**, signalée `policy: default`.
- `display_label` (à afficher) combine les deux : un rapport documenté mais périmé porte « DONNÉES PÉRIMÉES … ne pas considérer comme actuel ».
- L'index enregistre `data_as_of`, `max_data_age_days`, `freshness_policy` ; le dashboard calcule l'actualité **à l'ouverture**, jamais figée à la publication (index AI-001 sans ces champs : « actualité inconnue »).

## B. Intégrité : ce qui est détecté, ce qui ne l'est pas
`ReportStore.verify(expected_fingerprint=None)` détecte, **sans racine de confiance externe** :
index illisible · doublon d'entrée · lacune de versions · chemin hors stockage ou non conforme · fichier absent ou illisible · contenu modifié (empreinte) · identité du fichier ≠ entrée · métadonnée d'index ≠ rapport (titre, statut, simulation, décision, date, **niveau recalculé**) · **chaîne rompue** (une version réécrite, même avec son empreinte mise à jour dans l'index, ne correspond plus à l'empreinte citée par la version suivante) · fichier non référencé.

**Non détectable sans ancre externe** (démontré par test) : réécriture cohérente de la **dernière** version (fichier + index), suppression complète de la dernière version, remplacement de tout le stockage. Parade : `ReportStore.fingerprint()` après chaque publication légitime, conservé **hors du dépôt** (note privée, autre support), puis `verify(expected_fingerprint=…)`.
Hors de portée de l'outil : la falsification simultanée du stockage **et** de l'ancre.

## C. Vérification des faits
- Champ facultatif `claims[].verification_record` : vérificateur (`human` ou `collector` + identifiant ; **jamais un agent**), date, méthode (`primary_document_review`, `official_api_record`, `direct_observation`, `cross_source_agreement`), procédure (ex. `EVP-1`), preuves localisées (source citée par l'affirmation, emplacement, empreinte d'extrait facultative).
- Règles : uniquement sur un fait `verified` ; preuves réelles et citées ; vérification postérieure à la consultation de la preuve et antérieure au rapport.
- Un fait `verified` **sans trace** reste valide (compatibilité) mais plafonne le rapport à `partially_verified` (« vérification non documentée »).
- `intelligence/factcheck.promote_claim(...)` : promotion tracée → **nouvelle version** + correction motivée.
- Le validateur contrôle la **cohérence** d'une trace ; il ne prouve pas la **vérité** : la responsabilité est celle du vérificateur déclaré. Le libellé `fully_verified` l'énonce désormais (« VÉRIFICATION DOCUMENTÉE … verificateurs déclarés »).

## D. Contrat d'un fournisseur payant (`edge.paid_provider.v1`)
- `generate(agent_input, transport)` : `transport` (BillableTransport) est **le seul accès facturable** fourni par EDGE.
- Chaque `transport.request()` = **une réservation R4.2** (`reserved → attempt → result`) ; au-delà de `max_operations` : refus **avant** émission.
- Contrôle préalable : sans autorisation privée ou requête approuvée, le fournisseur **n'est pas invoqué**.
- Échec : débité (`result: error`), **aucune relance implicite** ; relance seulement si `max_attempts > 1`, et chaque relance réserve à nouveau.
- Réponse partielle / non structurée : débitée, `result: partial`, rejetée, jamais relancée.
- Transport fermé après l'exécution : inutilisable ensuite.
- Fournisseur payant sans ce contrat (opaque) : **refusé** (ses opérations internes ne seraient pas comptées).
- Limite : Python ne peut pas empêcher un fournisseur d'ouvrir sa propre connexion ; le contrat l'interdit, `tools.run_tests_offline` le détecte en test.

## E. Tests et retour arrière
`python -m tools.run_tests_offline` · `python -m unittest tests.test_ai001_1 -v`.
Retour arrière : `git revert <commit AI-001.1>` (aucune donnée publiée à migrer ; les index AI-001.1 contiennent 3 champs supplémentaires ignorés par le code AI-001).
