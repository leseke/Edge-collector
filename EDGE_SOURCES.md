# EDGE — Sources, preuves et entonnoir (R4)

EDGE reste **généraliste**. Le LEGO est la première catégorie de validation : références normalisées, dates de commercialisation et statistiques de ventes agrégées accessibles.

## Types de preuves (valeur probante décroissante pour une décision d'achat)
| Type | Sens | Peut fonder un BUY ? |
|---|---|---|
| `SOLD` | vente individuelle confirmée | oui (seule base possible d'un STRONG_BUY) |
| `SOLD_AGGREGATE` | statistiques agrégées de ventes (ex. BrickLink, 6 mois) | oui, **plafonné à BUY**, si tous les critères ci-dessous passent |
| `MARKET_TREND` | prix de marché indicatif (ex. tendance Cardmarket) | non → WATCH au mieux |
| `ASKING_PRICE` | annonce active | non (sert à trouver une offre, jamais à valoriser) |
| `RETAIL_OFFER` | offre boutique achetable | non (idem) |
| `AVAILABILITY` | disponibilité commerciale (dates, prix boutique) | non (contexte : fin de production) |
| `CULTURAL_SIGNAL` | Trends, Reddit… | non (hypothèse, jamais valorisation) |

Sans valorisation qualifiée : **WATCH** si une valorisation indicative existe, **NO_DATA** sinon. Pokémon et One Piece scellés ne bénéficient d'aucune exception.

## Critères de qualification d'une statistique agrégée pour un BUY
Configurables (`aggregate_policy`), choix de prudence et non constantes de marché :
fraîcheur ≤ 7 j · ≥ 10 unités vendues · ≥ 5 lots distincts · max/min ≤ 3 · écart moyenne simple/pondérée ≤ 20 % · état neuf · correspondance exacte de la référence · région Europe.
Scénarios : prudent = min(moyennes) − 10 %, central = moyenne pondérée, favorable = max(moyennes) ; jamais les min/max bruts. Chaque rapport liste chaque critère ✅/❌ et rappelle qu'il ne s'agit pas de ventes individuelles.

## Entonnoir
1. Prospection gratuite (eBay Browse : annonces actives).
2. Valorisation gratuite (BrickLink agrégé, Brickset disponibilité, TCGdex indicatif).
3. Confirmation **payante** (ventes individuelles eBay via Apify) uniquement pour les candidats WATCH/BUY non déjà confirmés.

### Verrou de dépense (couche d'exécution)
- L'autorisation vient **uniquement** de `config.private.json` :
  `"paid_investigation": {"authorized": true, "max_usd_per_run": 0.5, "est_usd_per_call": <coût relu>, "max_usd_per_month": <optionnel>}`.
  Placée dans `config.json` public, elle est ignorée (et signalée par le contrôle public/privé). Un champ de campagne ne peut rien autoriser.
- Montants : nombres finis, strictement positifs, non booléens ; `authorized` doit valoir exactement `true`. NaN, Infinity, `True`, 0, négatifs, texte : refusés.
- Toute source payante passe par `PaidGate` → `SpendGuard`, et l'adaptateur payant exige lui-même un garde (double verrou). Le garde n'accepte que les requêtes approuvées par l'entonnoir, plafonne les appels par run et, si renseigné, le cumul mensuel (journal privé `private/spend_ledger.jsonl`).
- R4.2 — **une opération externe = une réservation** : `PaidGate` réserve (journal `reserved`, débit), l'adaptateur payant consomme sans re-débiter (`attempt`), puis `result` (ok/erreur). Si l'appel externe n'a pas été tenté, la réservation est libérée (`released`). Une tentative échouée reste débitée (le fournisseur peut la facturer). Appel direct de l'adaptateur, réservation réutilisée ou détournée vers une autre requête : refusés.
- Le contrôle du plafond mensuel et l'écriture de la réservation se font sous **verrou interprocessus exclusif** (`fcntl` Linux/macOS, `msvcrt` Windows). Verrou indisponible ou non obtenu dans le délai : dépense refusée. Journal privé obligatoire.
- Aucun montant n'est publié : `paid_confirmation.reason`, le journal de coûts public et les logs n'affichent qu'une raison sans chiffre.
- Le coût est une **estimation** : fixer aussi un plafond de dépense côté fournisseur (console Apify).

### Limites restantes du verrou de dépense
- Le verrou Windows (`msvcrt`) est implémenté mais **non testé** (environnement de test Linux).
- Le verrou ne protège qu'**une seule machine** : un journal synchronisé entre plusieurs postes (OneDrive, Dropbox…) ne garantit pas le cumul mensuel. Ne pas exécuter de dépenses depuis deux machines.
- En CI (GitHub Actions), le journal n'est pas persistant : toute politique avec plafond mensuel y est refusée. Sans `config.private.json` en CI, aucune dépense n'y est de toute façon possible.
- Le plafond par run est propre à un processus ; c'est le plafond mensuel, sous verrou, qui borne les exécutions simultanées.
- Les ventes confirmées sont prises en compte au run suivant.

## Activation d'une source
`discovery/sources_access.json` (public, sans secret) : une source n'est appelée que si `status = VERIFIED` **et** ses variables d'environnement sont présentes. Sinon : `SKIPPED_UNAVAILABLE` avec la raison. État courant : `python -m tools.sources_status`.

## Accès encore nécessaires (rien n'a été testé en réel)
| Source | À faire | Points à confirmer |
|---|---|---|
| eBay Browse | compte développeur, application, `EBAY_CLIENT_ID/SECRET` | licence/conditions des Buy APIs et éligibilité de l'application ; quota réel du compte ; champs réels de la réponse (vendeur pro/particulier absent du résumé) |
| BrickLink | clé consommateur + jeton, 4 secrets | accès éventuellement réservé aux vendeurs ; enregistrement d'IP (GitHub Actions a des IP variables) ; valeur `region=europe` ; quota |
| Brickset | compte + `BRICKSET_API_KEY` | conditions d'usage ; zone DE utilisée comme approximation européenne |
| TCGdex | aucune clé | conditions d'usage ; couverture (cartes à l'unité seulement) |
| Apify (payant) | `APIFY_TOKEN`, plafond de dépense dans la console | tarif de l'acteur ; format d'entrée corrigé (`keywords`/`count`) à confirmer au premier appel |

Après relecture des conditions d'une source : passer son `status` à `VERIFIED`, renseigner `verified_by` / `verified_at`, ajouter les secrets.

## Pilote LEGO reproductible hors réseau
```
python -m discovery.cli --campaigns discovery/pilot_lego_campaigns.json \
  --offline-http discovery/fixtures/pilot_lego/http_routes.json \
  --as-of 2026-10-18T09:00:00+00:00 --out-dir /tmp/pilot --private-dir /tmp/pilot/priv
```
Réponses fictives au format documenté des API (sets 900xx inventés). Résultat attendu : 90001 BUY (agrégat qualifié, plafond BUY), 90002 WATCH (liquidité insuffisante), 90003 WATCH (dispersion), 90004 NO_DATA (aucune vente), display Pokémon scellé sans valorisation, carte Pokémon en tendance seulement, source payante bloquée.

## TCGdex — pilote (R4.3)
**Statut registre : VERIFIED (pilote)**, sur relecture de la documentation officielle (FAQ, schéma tarifaire, filtrage) ; à confirmer par l'utilisateur. Brickset, BrickLink, eBay et Apify restent `UNVERIFIED`.

Ce qui a été aligné sur le schéma documenté :
- une observation `MARKET_TREND` **par variante** (`normal`, `holo` via les champs `-holo`) ; clé produit `tcg:pokemon:<id>:<variante>` ;
- `observed_at` = date `updated` du fournisseur (fraîcheur réelle), `stale` au-delà de 7 jours ;
- aucune supposition : devise absente/non EUR, date illisible, prix nul ou absent ⇒ pas d'observation ; fournisseur omis ⇒ pas d'observation ;
- recherche paginée (`pagination:itemsPerPage`), au plus 2 requêtes de détail ;
- cache 24 h et enregistrement brut des réponses (`discovery/recording_http.py`).

Limites propres à la source (documentées par TCGdex) : prix parfois identiques entre raretés d'un même Pokémon, identifiants Cardmarket parfois erronés, cartes à l'unité uniquement. Preuve **indicative** : au mieux WATCH.

### Validation live (à exécuter sur ta machine)
Ni l'environnement de test de Claude (liste blanche réseau) ni son outil de lecture web (refus `robots.txt` de `api.tcgdex.net`, non contourné) n'ont pu joindre l'API.
```
python -m tools.tcgdex_probe --query pikachu --details 2
python -m tools.tcgdex_probe --query pikachu --details 2 --export-fixture   # puis relire tests/fixtures/tcgdex_live/
python -m unittest discover -s tests
```
Budget : au plus 3 requêtes HTTP (1 recherche + 2 détails), 0 si le cache de moins de 24 h est présent. La sonde affiche chaque requête (statut, cache, erreur), les anomalies de schéma par carte, les décisions, et écrit `private/tcgdex_probe/<horodatage>/` (réponses brutes, `latest.json`, `cost_journal.jsonl`, `probe_report.json`). Code retour 2 si une décision positive apparaissait sur la seule base d'un prix indicatif.
