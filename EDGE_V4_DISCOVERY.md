# EDGE — V4 + Discovery (branche de travail)

## Chaîne
Observation → Candidat → Investigation → Décision économique → Financement → Exécution (manuelle) → Suivi.

## V4 (règles)
- `capital_available = max(0, treasury − engaged)` ; montants dans `config.private.json` ou `EDGE_TREASURY`/`EDGE_ENGAGED`.
- La décision économique ne lit jamais le capital. `execution_ready` exige : signal, config valide, capital connu et suffisant, plafond d'allocation suffisant, offre achetable vérifiée.
- Statut global : `data_status` (OK/PARTIAL/FAILED/NO_DATA) et `posture` (SIGNALS/CASH/NO_CONCLUSION). CASH uniquement si couverture ≥ `min_coverage_for_cash`.
- `radar.json` public : aucun montant, aucun indicateur de financement (contrôlé par `assert_no_private_leak`). Financement : `private/run_private.json`.

## Discovery
- Campagnes : `discovery/campaigns.json` (réel, manuel), `discovery/demo_campaigns.json` (fixtures fictives).
- Preuves typées : `ASKING_PRICE`, `RETAIL_OFFER`, `SOLD`, `MARKET_TREND`. Une annonce n'est pas une vente.
- Mémoire : `data/discovery/store/ledger.jsonl` (append-only) + `candidates.json`. Décision initiale figée.
- Évaluation a posteriori : `discovery/outcomes.py` (cohorte complète, non concluant sous 20 résolus).

## Investigation
Rapport en 20 sections, frais déterministes (`investigation/fee_profiles.json`, **non vérifiés**), scénarios P25/médiane/P75, catalyseurs marqués HYPOTHÈSE/OBSERVÉ. STRONG_BUY impossible tant que les frais ne sont pas vérifiés.

## Search Lab
`python -m searchlab "LEGO Pokémon" --mode discovery` ou workflow `EDGE Search Lab` (manuel). Le dashboard prépare la recherche et affiche l'historique ; il n'exécute rien et ne détient aucun secret.

## Commandes
```
python -m unittest discover -s tests
python -m discovery.cli --campaigns discovery/demo_campaigns.json --fixtures discovery/fixtures/demo_observations.json --as-of 2026-10-18T09:00:00+00:00 --out-dir /tmp/edge-demo
python -m searchlab "LEGO 10399" --mode investigation --fixtures discovery/fixtures/demo_observations.json --out-dir /tmp/sl
```

## Publication : garde-fous
- `python -m tools.check_public_files [chemins]` : bloquant (code 1) si une clé financière privée ou un motif de secret apparaît. Par défaut : `radar.json` et `data/`.
- **Constat actuel** : `config.json` et le `radar.json` V3 déjà commité contiennent des montants (`capital_monthly`, `capital_max_available`, `capital_engaged`, `allocation_eur`). Ils restent aussi dans l'historique git : les retirer des fichiers courants ne les efface pas de l'historique.
- `python -m tools.split_private_config` : simulation par défaut ; `--apply` déplace les clés vers `config.private.json` sans changer les valeurs et sans créer `treasury`.
- Workflows : permissions en lecture seule, résultats en **artefact** (14 jours ; sur un dépôt public, téléchargeable par tout utilisateur GitHub connecté — le contenu est contrôlé par le garde-fou). Commit uniquement si `publish=true`, dans un job séparé qui seul reçoit `contents: write`, après un second contrôle.

## Campagne pilote (procédure)
1. Local, sans appel : `python -m discovery.cli --campaigns discovery/campaigns.json --out-dir /tmp/pilot --plan-only --only liquidite-watchlist --max-total-calls 3`
2. Local ou Actions avec `publish=false`, `max_total_calls=3`, `campaigns=liquidite-watchlist`.
3. Relire `cost_journal.jsonl` (appels, erreurs, durées, appels par source) et la facturation réelle Apify/Scavio du jour.
4. Relire `latest.json` : statut de chaque appel, `simulated=false`, cohérence des ventes avec les annonces eBay réelles (contrôle manuel d'un échantillon).
5. Seulement ensuite : élargir à une campagne Scavio, puis envisager `publish=true`.

## R4 — Sources officielles et entonnoir
Voir `EDGE_SOURCES.md` : types de preuves, critères des statistiques agrégées, entonnoir payant, registre d'accès, pilote LEGO hors réseau.
