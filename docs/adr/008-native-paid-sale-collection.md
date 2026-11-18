# Collecte de ventes payées par EDGE

Le Radar a besoin de ventes éligibles et traçables pour recalculer les repères à chaque lecture. Options examinées :

- Tâche conversationnelle et commits de données. Facile à amorcer, mais dépend d'un autre service et d'un redéploiement à chaque vente.
- Déclencheur Cloudflare existant et persistance D1. EDGE reçoit les observations au prochain chargement du Radar.

Retenir le second chemin. Le Worker lance une seule requête Gemini groupée par jour UTC pour les quatre familles de produits et d'événements. Gemini fournit des liens candidats ; seul le contenu public de la page GCC peut établir une vente payée. Le collecteur vérifie le domaine, la référence, la langue, l'édition, le grade, la date et le prix EUR avant insertion. Un résultat inaccessible, ambigu ou incomplet ne devient pas une observation. Aucun appel de modèle pour l'analyse ni transfert de pistes privées.

Deux tables additives isolent cette collecte du prix agrégé TCGdex. `paid_sale_scans` enregistre le jour, l'état et les compteurs. `paid_market_sales` porte l'identifiant du lot, la clé de variante, la date, le montant en centimes, l'URL, la date d'observation et le SHA-256 du document. La clé du lot rend les réinsertions idempotentes. Aucun changement aux routes publiques et aucun nouvel accès HTTP en écriture. Le serveur du Radar interroge D1 et réutilise les règles court/long terme.

Critère d'acceptation : un cycle simulé avec une page payée écrit une vente une seule fois, puis le moteur du Radar la retrouve sous la variante exacte et peut recalculer à partir d'elle. Un cycle live doit ensuite démontrer la recherche, la validation et la lecture D1 avant d'annoncer l'activation. La branche de développement conserve le référentiel vérifié lors d'une panne D1. Enlever l'opt-in Cloudflare arrête les appels Gemini sans effacer les ventes.

## Activation de l'environnement isolé

1. Appliquer `cloud/collector/schema.sql` à la base de développement via Wrangler. Les nouvelles tables sont additives.
2. Sur le Worker du collecteur, configurer le secret `GEMINI_API_KEY` avec une clé d'un projet Gemini du niveau gratuit, sans compte de facturation associé, puis la variable `GEMINI_FREE_TIER_ENABLED=true`. Le code ne peut pas vérifier le niveau de facturation d'une clé. Déployer le collecteur avec le déclencheur de collecte quotidien et le binding D1 `DB`.
3. Configurer le binding D1 `SALES_DB` du Worker d'interface sur cette même base. Cette liaison est facultative pour les déploiements sans collecteur. Éviter les identifiants d'environnement dans le code applicatif.
4. Vérifier dans D1 `paid_sale_scans` et `paid_market_sales`, puis ouvrir le Radar et comparer la variante, le nombre de ventes et le prix. En cas d'échec ou de résultat vide, inspecter le passage suivant avant de conclure à une couverture réelle.

Sans activation, la prévisualisation continue d'afficher l'historique déjà documenté. Les pages d'enchères source peuvent refuser la lecture ou évoluer. Les tests locaux simulent les réponses externes et vérifient le comportement avec SQLite.

## Recherche par famille et calcul des tendances

Chaque jour, le Worker traite les quatre familles (cartes, boosters et displays, coffrets scellés, et sorties/événements). La même requête Gemini demande une section par famille, avec au plus huit liens retenus, dont deux lots à vérifier. Une section manquante donne un passage partiel si d'autres sections sont présentes, une section signalée vide est acceptée. Le Worker ignore les doublons de liens du passage quotidien. Un refus de quota ou de facturation arrête le passage sans fournisseur de repli. Le Worker doit utiliser un projet Gemini non facturé et des services Cloudflare du plan gratuit. Ce mode couvre l'univers de recherche par échantillonnage, sans prétendre indexer toutes les annonces des plateformes. Les annonces et publications sont enregistrées comme liens candidats, avec la famille de la recherche et le jour de découverte. L'accès, le prix, la disponibilité et le rattachement à un produit restent à confirmer.

Les lots gradés et scellés GCC peuvent être analysés si la page indique le prix final en EUR, le statut payé et une identité assez précise. Pour les scellés, un titre explicite est requis. Les conditions des cartes brutes et les prix de ventes sur d'autres plateformes restent à intégrer. La clé de variante préserve série, référence ou présentation, langue, édition et grade ou scellement. Les dossiers existants restent compatibles.

Le Radar compare deux fenêtres de 30 jours pour chaque variante, avec trois ventes vérifiées minimum par fenêtre. Un scénario conditionnel directionnel est affiché si la médiane évolue d'au moins 10 % et que le volume observé ne diminue pas. Ce signal n'est pas une probabilité, un prix futur ou la preuve d'une réaction à une annonce. Il reste à valider et dater les événements puis à les rattacher aux variantes pour mesurer les réactions historiques et comparer des cycles similaires.

Quand l'historique de la variante le permet, EDGE mesure aussi le nombre de mouvements comparables suivis d'une poursuite dans la même direction. Le calcul utilise jusqu'à 360 jours, avec des séquences historiques non chevauchantes de trois fenêtres et sans les deux fenêtres qui donnent le signal actuel. Le rapport décrit les cas observés sans les convertir en probabilité future.
