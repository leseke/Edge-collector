# Historique Git — exposition des données financières (décision à prendre)

**Rien n'a été réécrit.** Ce document prépare une décision ; il ne l'exécute pas.

## Constat (vérifié le 2026-10-18 sur le dépôt public)
- Dépôt `leseke/Edge-collector` : **public**, GitHub Pages **actif**, 0 fork.
- Valeurs ayant été publiées : `capital_monthly = 300`, `capital_max_available = 600`, `capital_engaged = 0`, `capital_available = 600`, et des fourchettes `allocation_eur` dérivées. **Aucune trésorerie réelle (`treasury`) n'a jamais été publiée.**
- Période : du 2026-10-08 (création de `config.json`) à aujourd'hui ; `radar.json` présent dans 12 commits de `main`.
- Références existantes : `main`, `feature/discovery-v1-foundation`, `refs/pull/1/head`, `refs/pull/1/merge`.

## Ce que l'assainissement actuel fait et ne fait pas
- Fait : les fichiers courants ne contiennent plus de montant (contrôle `--tracked` : 0 anomalie), et un test empêche toute réintroduction.
- Ne fait pas : les anciens commits restent consultables (interface GitHub, clones existants, caches, `refs/pull/*`).

## Options
| Option | Effet | Coût / risque |
|---|---|---|
| A. Ne pas réécrire | Les valeurs passées restent visibles | Aucun. Défendable si l'on considère ces montants (budget de principe 300/600) comme peu sensibles et désormais caducs. |
| B. Réécrire l'historique (`git filter-repo`) + force-push | Les commits réécrits ne contiennent plus les clés | Change tous les SHA ; casse les clones, la PR #1 et la branche de travail (à rebaser) ; ne purge **ni** `refs/pull/*` **ni** les caches GitHub sans demande au support GitHub. |
| C. Passer le dépôt en privé | Coupe l'accès public futur | GitHub Pages en dépôt privé dépend de l'offre du compte : à vérifier avant. |

Recommandation de prudence : décider A ou B **avant** de fusionner quoi que ce soit, car B réécrit aussi la base de cette branche.

## Option B — commandes préparées (NE PAS lancer sans validation)
À exécuter sur un **clone miroir neuf**, jamais sur la copie de travail :
```
git clone --mirror https://github.com/leseke/Edge-collector.git edge-mirror.git
cd edge-mirror.git
pip install git-filter-repo
# Remplace les valeurs dans config.json et radar.json de TOUT l'historique :
git filter-repo --replace-text ../expressions.txt
#   expressions.txt :
#   regex:"capital_monthly":\s*[0-9.]+==>"capital_monthly": null
#   regex:"capital_max_available":\s*[0-9.]+==>"capital_max_available": null
#   regex:"capital_engaged":\s*[0-9.]+==>"capital_engaged": null
#   regex:"capital_available":\s*[0-9.]+==>"capital_available": null
#   regex:"allocation_eur":\s*\[[^\]]*\]==>"allocation_eur": null
# Vérifier AVANT de pousser :
git log --all -p | grep -E '"capital_(monthly|max_available|engaged|available)": *[0-9]' && echo "ENCORE PRÉSENT"
git push --force --mirror   # irréversible côté GitHub
```
Puis : rebaser `work/v4-discovery` sur le nouveau `feature/discovery-v1-foundation`, et demander au support GitHub la purge des vues en cache et de `refs/pull/1/*` si nécessaire.
