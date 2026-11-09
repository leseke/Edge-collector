# EDGE — Comparaison des trajectoires mensuelles

Analyse rétrospective ordonnée sur des maxima mensuels polonais en PLN. Aucune estimation de marge nette ni de prix de vente encaissé.

Configurations de quatre mois : 79147. Requêtes de test déterministes : 200.

Les précédents appartiennent à d’autres références présumées et leur résultat doit se terminer avant le mois du signal testé. Les mois manquants interrompent la trajectoire. Les dates de publication historiques et révisions ne sont pas vérifiées.

| Horizon | Tests appariés | MAE analogues (points de %) | MAE aucun changement | MAE médiane passée | Brier analogues | Brier fréquence passée | Faux signaux de hausse |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 mois | 156 | 6.5311 | 6.9494 | 6.9494 | 0.2365 | 0.2456 | 31 |
| 3 mois | 115 | 13.0976 | 13.9530 | 14.0158 | 0.2635 | 0.2523 | 34 |
| 6 mois | 88 | 20.9753 | 24.7726 | 22.1305 | 0.1703 | 0.1962 | 21 |
| 12 mois | 38 | 31.7258 | 42.5205 | 28.9027 | 0.1024 | 0.1016 | 4 |

MAE et score de Brier : une valeur plus basse est préférable. Les références et le modèle sont évalués sur les mêmes requêtes mesurables. Les faux signaux sont des estimations de hausse dont le maximum mensuel cible ne monte pas ; ils ne représentent pas des opérations financières.

## Exemple fixé avant mesure : série source 10312, juin 2023

Cette date est la fin de l’historique. Ses résultats futurs restent inconnus dans le fichier ; les estimations ci-dessous ne constituent pas une prévision actuelle.

| Horizon | Précédents retenus | Fréquence historique de hausse | Médiane des évolutions | Dispersion p10–p90 |
|---|---:|---:|---:|---|
| 1 mois | 20 | 40.0000 % | 0.0000 % | -4.0518 % à 8.5873 % |
| 3 mois | 20 | 55.0000 % | 4.2047 % | -10.5554 % à 13.9897 % |
| 6 mois | 20 | 60.0000 % | 5.5997 % | -10.0173 % à 23.1201 % |
| 12 mois | 20 | 80.0000 % | 14.3123 % | -2.0172 % à 55.8778 % |

## Couverture du test et erreurs de direction

| Horizon | Requêtes choisies | Estimation suffisante | Résultat après fin du fichier | Série incomplète | Hausses correctes | Fausses hausses | Hausses manquées | Absences de hausse correctes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 mois | 200 | 195 | 20 | 20 | 27 | 31 | 38 | 60 |
| 3 mois | 200 | 194 | 20 | 62 | 47 | 34 | 21 | 13 |
| 6 mois | 200 | 191 | 40 | 68 | 65 | 21 | 2 | 0 |
| 12 mois | 200 | 190 | 80 | 80 | 34 | 4 | 0 | 0 |

Une fréquence estimée de hausse au moins égale à 50 % classe le résultat comme hausse. Les résultats manquants ne sont pas comptés comme des baisses.


## Portée et limites

Règles fixées pour cette version : trois variations mensuelles successives, saison à ±1 mois, rapport de prix au moins 0,5, distance moyenne des variations logarithmiques au plus 0,10, vingt voisins maximum et dix références présumées minimum. Ces choix n’ont pas été optimisés ni validés pour la prévision.

Les estimations, écarts et exemples sont archivés avec les mois et lignes sources dans trajectory_research.json.gz. Les fenêtres et marchés sont dépendants ; la disponibilité à l’époque des données, les variantes et la représentativité ne sont pas établies. La sélection des requêtes précède le contrôle de leurs résultats futurs.

**Avantage prédictif non établi.** Aucun signal d’achat ou de revente actuel n’est émis.
