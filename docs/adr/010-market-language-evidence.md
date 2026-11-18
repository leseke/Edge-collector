# Langue de catalogue et langue des observations Pokémon

TCGdex peut renvoyer les mêmes agrégats Cardmarket pour deux fiches localisées. Utiliser la langue de la fiche sur le prix créerait une comparaison artificielle. EDGE conserve le prix indicatif avec `marketLanguage: null`, indique sa portée dans Explorer et ajoute l'italien au catalogue. Le Radar continue de grouper les ventes par clé de variante, qui comprend la langue et le grade ou le scellement.

Sur une fiche catalogue, les ventes documentées ne sont affichées que si leur clé associe explicitement le même identifiant TCGdex et la même langue. Les autres rapprochements restent documentaires. Aucun schéma D1 ni identifiant de produit historique ne change. Vérification attendue : une même fiche française et italienne peut avoir le même repère agrégé, tandis que les ventes explicites françaises sont absentes de la fiche italienne.
