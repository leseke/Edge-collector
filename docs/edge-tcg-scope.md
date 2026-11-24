# EDGE — périmètre TCG

## Périmètre produit

EDGE ne suit que les jeux de cartes à collectionner et leur écosystème direct :

- Pokémon, One Piece Card Game, Magic: The Gathering, Yu-Gi-Oh!, Disney Lorcana, Digimon Card Game, Riftbound, Flesh and Blood, Weiss Schwarz, Union Arena, Dragon Ball Super Card Game et Star Wars Unlimited.
- Cartes brutes ou gradées, promos, éditions limitées, erreurs d'impression et produits scellés.
- Accessoires officiels, produits de tournoi, goodies et collaborations directement liés à un TCG.

Sont hors périmètre : LEGO, Funko, consoles et collectibles sans lien direct avec un TCG. Une licence commune ne suffit pas : un set LEGO One Piece n'est pas un produit TCG.

## Garde-fous implémentés

- `discovery/campaigns.json` déclare `scope_policy: TCG_ONLY`.
- Chaque campagne active doit porter `scope: TCG_ONLY` et ses requêtes statiques doivent identifier un jeu TCG.
- Les requêtes contenant des catégories explicitement exclues sont rejetées.
- Les campagnes LEGO historiques ont été conservées dans `discovery/campaigns_archive_legacy.json`, mais ne figurent plus dans le registre actif.
- La revalidation de production ne réinterroge que les candidats dont le jeu TCG est identifiable. Les candidats historiques ambigus ou hors périmètre sont ignorés.
- Les campagnes de démonstration historiques restent compatibles avec leurs fixtures ; elles ne constituent pas des campagnes de production.
- L'expansion de recherche utilise des références numériques de produits sans imposer le format d'identifiant LEGO.

## Limites connues — migration incomplète

Le périmètre TCG du moteur Discovery est renforcé, mais toute l'application n'est pas encore migrée :

- `collect.py` conserve une watchlist mixte historique ; Discovery ne retient que les entrées portant explicitement un champ `game` TCG.
- `commercial_targets.json` contient encore des cibles LEGO.
- Le workflow `.github/workflows/commercial-history.yml` et `scripts/discovery_history.py` gardent des hypothèses LEGO (références numériques, LDLC et contrôles de marque).
- Les archives et fixtures historiques ne sont pas des données de marché TCG et ne doivent pas alimenter les recommandations EDGE TCG.

**Conséquence :** ne pas considérer le pipeline « commercial history » comme migré ou comme source de données TCG. Sa migration doit être un chantier distinct : catalogue de cibles TCG, identifiants canoniques par jeu/produit, sources adaptées, fixtures réelles qualifiées et tests dédiés. Les archives doivent rester consultables sans être réinjectées dans les campagnes actives.

## Politique de données et de coûts

- Les campagnes produisent des observations, pas directement des recommandations d'achat.
- Prix affichés, prix indicatifs agrégés et ventes conclues restent des types de preuve distincts.
- Une absence de données n'est pas une absence de demande.
- Les sources payantes restent soumises au SpendGuard ; aucun appel payant n'est autorisé par le seul contenu d'une campagne.
- Aucune API payante, dépense ou action d'achat n'a été déclenchée par cette migration.
