# EDGE — interface, décisions et comptes rendus

## Objectif

L'interface doit transformer un moteur d'analyse complexe en décisions compréhensibles. Elle ne doit ni masquer l'incertitude, ni faire passer une observation pour une preuve, ni présenter une hypothèse comme une recommandation certaine.

## Principes d'interface

1. **Une question par écran.** Vue d'ensemble = que se passe-t-il ? Recherche = que sait-on de cet objet ? Opportunités = pourquoi l'examiner ? Surveillance = qu'est-ce qui change ? Portefeuille = quelle est ma situation réelle ? Rapports = comment EDGE est-il arrivé à sa conclusion ?
2. **Synthèse avant détail.** Afficher d'abord la conclusion, son niveau de fiabilité, le prix d'entrée observé ou manquant, le risque principal et l'action de suivi. Déplier ensuite l'analyse et les preuves.
3. **Langage courant.** Tout statut technique visible doit être traduit en français et expliqué au premier usage.
4. **Traçabilité.** Chaque fait important doit pouvoir être relié à une source, une date d'observation et un type de preuve.
5. **Incertitude visible.** Les données manquantes, partielles, périmées ou contradictoires sont affichées comme telles.
6. **Aucune pression à l'achat.** La recherche et la surveillance restent utiles même avec un budget disponible de zéro.

## Vocabulaire commun des preuves

| Code | Libellé utilisateur | Définition |
|---|---|---|
| FACT | Fait documenté | Une source identifiable étaye directement l'information. Le fait peut encore nécessiter une vérification indépendante. |
| WEAK_SIGNAL | Signal faible | Indice isolé ou incomplet qui mérite une surveillance, sans suffire à conclure. |
| INFERENCE | Déduction | Interprétation issue de plusieurs observations ; ce n'est pas une preuve directe. |
| BET | Hypothèse risquée | Thèse prospective qui assume l'incertitude et doit indiquer ses conditions d'invalidation. |

Les niveaux de preuve ne sont pas des notes de qualité et ne doivent pas être agrégés en un score opaque.

## Statuts de décision lisibles

| Code interne | Affichage |
|---|---|
| WATCH | À surveiller |
| INVESTIGATE | Approfondir |
| WAIT | Attendre un meilleur point d'entrée ou davantage de preuves |
| PASS | Écarter pour le moment |
| NO_DATA | Données insuffisantes |
| RESEARCH_ONLY | Analyse informative, non exploitable comme décision |
| PENDING | Vérification en attente |

Un statut ne remplace jamais son explication. « À surveiller » doit préciser ce qui justifie la surveillance et quel événement ferait évoluer le dossier.

## Format obligatoire d'un compte rendu

Chaque rapport d'investigation ou de décision comporte les sections suivantes, même si certaines indiquent explicitement « non disponible » :

1. **Résumé décisionnel** — objet exact, jeu, extension, langue/région, statut, date du rapport, horizon et conclusion en une phrase.
2. **Pourquoi EDGE l'a retenu** — signaux qui ont déclenché l'analyse et critères de sélection.
3. **Ce qui est établi** — faits, sources, horodatages, variantes et périmètre réellement vérifiés.
4. **Ce qui est seulement suggéré** — signaux faibles et inférences, avec leur raisonnement.
5. **Thèse / pari éventuel** — catalyseurs, acteurs, incitations, mécanisme de marché et conditions nécessaires.
6. **Contre-thèse** — éléments contradictoires, scénarios d'invalidation et explications alternatives.
7. **Marché et liquidité** — listings séparés des ventes conclues ; volume, profondeur, spread et concentration uniquement si mesurés.
8. **Économie de l'opération** — prix d'entrée, frais, grading éventuel, coûts de détention, prix net de sortie et hypothèses. Les inconnues restent visibles.
9. **Scénarios** — prudent, central et favorable uniquement si les données permettent de les construire ; hypothèses et horizon explicites, jamais de rendement garanti.
10. **Prochaine vérification** — donnée manquante, source à consulter, seuil ou événement qui ferait évoluer la décision.
11. **Journal des changements** — ce qui a changé depuis le rapport précédent et pourquoi.

## Règles de présentation des prix

- Prix affiché, prix agrégé indicatif, offre disponible et vente conclue sont des catégories distinctes.
- Une estimation ne doit jamais être libellée « valeur réelle ».
- Une vente conclue exige une preuve de transaction exploitable et une correspondance de variante, langue, état et grade.
- Le prix net de revente déduit les frais et coûts connus ; les coûts inconnus sont signalés.
- Une absence de transaction observée ne prouve pas une absence de demande.

## Explication des conclusions

Toute conclusion doit répondre en français à quatre questions :

- **Pourquoi cette conclusion ?** Citer les observations déterminantes.
- **À quel point est-elle solide ?** Décrire couverture, fraîcheur, indépendance et qualité des sources, sans score arbitraire.
- **Qu'est-ce qui pourrait la rendre fausse ?** Donner les principaux risques et éléments contraires.
- **Que faut-il faire ensuite ?** Proposer une action de recherche/surveillance proportionnée, sans pousser à acheter.

## Trois niveaux de lecture

- **Rapide :** conclusion, intérêt, risque principal, prix d'entrée et prochaine action.
- **Analyse :** thèse, acteurs, offre/demande, catalyseurs, liquidité, coûts et scénarios.
- **Preuves :** sources originales, horodatages, observations brutes, méthode et journal des corrections.

## Historique des rapports — première version

La page `/local` conserve jusqu’à 20 résultats d’enquête dans le `localStorage` du navigateur. Elle n’enregistre ni le jeton d’accès ni le corpus importé. Un rapport peut être rouvert et comparé structurellement à un autre rapport (décision EDGE, nombre d’affirmations, sources et jeux de données). La comparaison repère les affirmations ajoutées/retirées et les changements de formulation, qualification, vérification, confiance et références sources ; elle repère aussi les sources et jeux de données ajoutés/retirés/modifiés ainsi que les questions ouvertes apparues ou résolues. Les rapprochements reposent sur les identifiants stables : un identifiant renouvelé est signalé comme un ajout/retrait, pas automatiquement rapproché par similarité de texte. Elle ne juge pas elle-même la qualité ou la véracité d’une nouvelle preuve. L’historique est propre au navigateur et n’est pas synchronisé entre appareils ; il ne remplace pas encore un journal serveur durable.


### Archive locale persistante

Le compagnon Python expose aussi une archive authentifiée :
- GET /v1/reports renvoie les métadonnées publiques des rapports versionnés, sans chemin interne ni empreinte de stockage.
- GET /v1/reports/{report_id}?version={n} relit une version immuable et son dossier d'enquête associé.
- Les deux routes exigent le jeton Bearer local, les mêmes contrôles loopback et l'origine autorisée que l'enquête.
- L'identifiant de rapport est validé avant lecture ; le chemin du dossier est résolu et borné au répertoire d'archive.
- L'interface peut charger l'archive du compagnon, rouvrir une version et la recopier dans l'historique du navigateur pour la comparer.
- Effacer la copie du navigateur ne supprime jamais l'archive persistante du moteur.

La persistance serveur reste locale à l'installation EDGE ; elle n'est pas synchronisée dans le cloud ni entre plusieurs ordinateurs.

## État de réalisation

Ce document définit le contrat produit visé. Le guide visuel des niveaux FACT / WEAK_SIGNAL / INFERENCE / BET est raccordé aux pages d'accueil et d'intelligence de réaction. Les rapports d'investigation complets, les pages de recherche/opportunités et leur liaison au moteur réel restent à implémenter. Ne pas présenter ce document comme une fonctionnalité déjà entièrement livrée.
