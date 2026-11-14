# AI-002B — Intégration contrôlée d'un fournisseur OpenAI

**Intégration technique, désactivée par défaut. Aucune dépense, aucun déploiement, aucun appel réel effectué.**

## 1. Diagnostic initial (démontré avant correction)
- Base : 237 tests hors ligne, 0 tentative réseau ; SDK `openai` absent ; `requests` présent.
- **Publication** : `run_inquiry` publiait le rapport *puis* écrivait le dossier → un échec d'écriture laissait un rapport publié sans dossier (reproduit).
- **Calculs** : « hausse de 420 % » acceptée car 420 figure dans la source (420 → 545 = +29,8 %) : une citation ne garantit pas un calcul (reproduit).
- **Isolation** : une injection reformulée n'est pas vue par le filtre lexical (reproduit) → la protection doit être structurelle.
- **Chemin payant** : `run_inquiry` ne transmettait aucun canal d'envoi : tout fournisseur payant y était inutilisable.

## 2. Architecture retenue
```
GitHub Pages (statique, public, AUCUN secret)  ←  data/intelligence/ (rapports + dossiers publiés, commit explicite)
                                                   ↑ publication manuelle (--store data/intelligence)
Poste de l'utilisateur (environnement sécurisé)
  python -m intelligence.ask "question" --provider openai --model <explicite>
    → planificateur (corpus autorisé) → OpenAIResponsesProvider
       → BillableTransport (R4.2 : 1 opération = 1 réservation) → envoi REST (clé en en-tête)
    → validation stricte → calculs EDGE → conformité → ingestion → publication rapport+dossier
  config.private.json (plafonds), private/spend_ledger.jsonl (journal), OPENAI_API_KEY (environnement)
```
**Alternatives rejetées** : appel depuis le navigateur (clé exposée) ; proxy serverless / fonction cloud (nouveau service à déployer et sécuriser — non autorisé) ; GitHub Actions (journal de dépense non persistant : le plafond mensuel R4.2 y est refusé ; utilisable plus tard sans plafond mensuel, après validation) ; SDK `openai` (dépendance et version supplémentaires, alors que l'API REST documentée suffit).

## 3. Fournisseur OpenAI (`intelligence/providers/openai_responses.py`)
Interface ciblée : **Responses API**, `POST https://api.openai.com/v1/responses` ; sortie structurée `text.format = {type: "json_schema", name, schema, strict: true}` ; `store: false` ; `max_output_tokens` borné ; **aucun outil fourni**.
- Consignes EDGE statiques dans `instructions` ; toutes les données dans **un** message utilisateur, encapsulées `{"untrusted_data": …}`.
- Le statut n'est jamais jugé suffisant (des réponses tronquées marquées `completed` ont été signalées) : la sortie est toujours analysée puis validée contre son schéma.
- Réponse partielle (`incomplete`, refus, JSON tronqué, élément de sortie autre que `message`/`reasoning` — dont tout appel d'outil) → `partial`, débitée, rejetée, jamais relancée.
- 429, 5xx, délai : erreur journalisée, **aucune relance implicite** ; le message d'erreur ne reprend jamais le corps de la réponse (qui pourrait refléter la clé).
- Activation : `EDGE_OPENAI_ENABLED=1` + `OPENAI_API_KEY` + registre `openai` `VERIFIED` + `SpendGuard` autorisé. Sinon **refus avant toute réservation et tout appel**. Aucun modèle par défaut.
- Un abonnement ChatGPT ne couvre pas l'API : compte API facturé séparément (noté au registre).
- Mock (`mock_openai.py`) : reproduit le **contrat HTTP** de la Responses API ; il ne remplace que l'envoi : construction de requête, analyse, réservations R4.2 sont exercées à l'identique.

## 4. Correctifs des trois risques
**Preuves / calculs — contrat `edge.agent_output.v2`** (schémas stricts, `intelligence/agent_v2.py`) : `facts` = références `extract_id` (texte recopié par EDGE, ni retapé ni altérable) · `computations` = demandes (méthode, dataset, fenêtre) **calculées par EDGE**, un résultat annoncé différent est rejeté · `interpretations` = texte du modèle, jamais vérifié, fondement obligatoire ; ses nombres doivent venir de ses faits ou des **résultats** EDGE, et un pourcentage doit être un pourcentage de la preuve ou un résultat de variation (un prix de 420 ne justifie pas « 420 % ») · `hypotheses`/`uncertainties`/`limitations` sans chiffre. Schéma de rapport **1.2.0** (ajouts facultatifs) : `kind: interpretation`, `basis`, `computations` (méthode, entrées exactes, résultat, `computed_by: edge_engine`) — **recalculés à chaque validation**.

**Isolation structurelle** : aucune capacité n'est atteignable depuis une sortie de modèle — pas d'outil fourni, élément d'appel d'outil rejeté ; sortie = données validées par schéma strict (aucun champ de décision, d'allocation ou de publication possible) ; décision EDGE fournie par EDGE ; consignes et données séparées ; entrée du modèle construite sans configuration privée ni variable d'environnement ; clé seulement dans l'en-tête HTTP. Le filtre lexical reste une défense d'appoint.

**Publication cohérente** : `ReportStore.publish(report, dossier)` en deux phases — écriture exclusive (O_EXCL + fsync) du rapport puis du dossier, puis **remplacement atomique de l'index = point de validation**, fsync du répertoire (POSIX). Erreur avant validation : fichiers créés supprimés, rien n'est publié. Interruption brutale : fichiers non référencés, signalés par `verify()`, mis en quarantaine (jamais supprimés) par `recover()`. L'espace `eir_q-*` (enquêtes d'agent) exige son dossier ; le dossier doit correspondre à l'empreinte du rapport ; `verify()` contrôle aussi les dossiers.

**Garanties effectives du système de fichiers** : `os.replace` est atomique sur un même volume local (POSIX ; NTFS via remplacement) ; `O_EXCL` empêche tout écrasement ; le verrou interprocessus protège **une seule machine**. **Non garanti** : volumes réseau, dossiers synchronisés (OneDrive, Dropbox) — la synchronisation peut réordonner ou dupliquer des fichiers ; ne pas y placer `data/intelligence/` lors d'une publication. Le fsync de répertoire n'existe pas sous Windows.

## 5. Recherche externe (contrat seul, `intelligence/external_sources.py`)
`edge.external_source.v1` : URL (https), provenance, date de collecte (avec fuseau), extraits exacts localisés (+ empreinte facultative), disponibilité, droits (`quote_only`/`summary_only`/`full`/`unknown`, citations courtes si inconnus), coût (une récupération payante exige une réservation R4.2), confiance, conflits. Conversion vers le corpus en `unverified`. Registre `web_search` : `UNVERIFIED`, aucun fournisseur.

## 6. Exemples
- `intelligence/examples/ai002b/` : enquête complète par le **faux fournisseur** (2 opérations simulées, 2 réservations dans un journal privé simulé), faits par références, calcul EDGE `pct_change` (+29,76 %), interprétation fondée, décision `NOT_EVALUATED`.
- `intelligence/examples/ai002a/` : régénéré avec la publication conjointe (l'ancien dossier, écrit hors index, serait signalé orphelin).

## 7. Commandes
```
python -m tools.run_tests_offline
python -m intelligence.ask "…question…" --provider mock-openai --store /tmp/demo
python -m intelligence.ask "…" --provider openai --model <modele>      # refusé tant que non activé
```

## 8. Opérations encore interdites
Appel OpenAI réel · toute dépense réelle · passage du registre `openai` ou `web_search` à `VERIFIED` sans validation indépendante · recherche web (gratuite ou payante) · publication automatique · déploiement d'un service · exécution en CI avec plafond mensuel · modification d'allocation ou décision BUY/STRONG_BUY par un modèle · statut `complete`/`fully_verified` pour un rapport généré.

## 9. Retour arrière
`git revert <commit AI-002B>`. Effets : retour au schéma 1.1 (rapports 1.2 publiés entre-temps seraient refusés par l'ancien validateur : n'en publier aucun avant validation) ; l'exemple AI-002A redevient celui d'AI-002A.
