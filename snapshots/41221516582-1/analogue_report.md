# EDGE — Comparaison de configurations historiques

Méthode : RETAIL_EVENT_ANALOGUES_V1. Chaque recherche est figée à la détection de son événement.

| Produit | Horizon | Précédents comparables mesurés | Fréquence calculée |
|---|---:|---:|---|
| lego_40744 | 24 h | 0 | Données insuffisantes |
| lego_40744 | 72 h | 0 | Données insuffisantes |
| lego_40744 | 168 h | 0 | Données insuffisantes |

Le score de ressemblance est une règle de recherche non calibrée, pas une probabilité. Les poids, le seuil de 0,75 et le minimum de cinq produits ne constituent pas une validation prédictive.

Les caractéristiques utilisent seulement le prix, le mois, le vendeur et la variation de prix connue avant la détection. Licence, distribution, quantités produites, ventes et marge ne sont pas renseignées.

Les événements futurs, les résultats encore inconnus à la date du signal et les répétitions du même produit sont exclus. Les motifs et empreintes sont conservés dans analogue_matches.json.

Aucune performance hors échantillon ni fenêtre optimale d’achat ou de revente n’est établie.
