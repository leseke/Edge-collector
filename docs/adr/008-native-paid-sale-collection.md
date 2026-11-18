# Collecte de ventes payées par EDGE

Le Radar a besoin de ventes éligibles et traçables pour recalculer les repères à chaque lecture. Options examinées :

- Tâche conversationnelle et commits de données. Facile à amorcer, mais dépend d'un autre service et d'un redéploiement à chaque vente.
- Déclencheur Cloudflare existant et persistance D1. EDGE reçoit les observations au prochain chargement du Radar.

Retenir le second chemin. Le Worker demande au plus une recherche Gemini par jour UTC pour des références publiques. Gemini fournit des liens candidats ; seul le contenu public de la page GCC peut établir une vente payée. Le collecteur vérifie le domaine, la référence, la langue, l'édition, le grade, la date et le prix EUR avant insertion. Un résultat inaccessible, ambigu ou incomplet ne devient pas une observation. Aucun appel de modèle pour l'analyse ni transfert de pistes privées.

Deux tables additives isolent cette collecte du prix agrégé TCGdex. `paid_sale_scans` enregistre le jour, l'état et les compteurs. `paid_market_sales` porte l'identifiant du lot, la clé de variante, la date, le montant en centimes, l'URL, la date d'observation et le SHA-256 du document. La clé du lot rend les réinsertions idempotentes. Aucun changement aux routes publiques et aucun nouvel accès HTTP en écriture. Le serveur du Radar interroge D1 et réutilise les règles court/long terme.

Critère d'acceptation : un cycle simulé avec une page payée écrit une vente une seule fois, puis le moteur du Radar la retrouve sous la variante exacte et peut recalculer à partir d'elle. Un cycle live doit ensuite démontrer la recherche, la validation et la lecture D1 avant d'annoncer l'activation. La branche de développement conserve le référentiel vérifié lors d'une panne D1. Enlever l'opt-in Cloudflare arrête les appels Gemini sans effacer les ventes.

## Activation de l'environnement isolé

1. Appliquer `cloud/collector/schema.sql` à la base de développement via Wrangler. Les nouvelles tables sont additives.
2. Sur le Worker du collecteur, configurer le secret `GEMINI_API_KEY` avec une clé d'un projet Gemini du niveau gratuit, sans compte de facturation associé, puis la variable `GEMINI_FREE_TIER_ENABLED=true`. Le code ne peut pas vérifier le niveau de facturation d'une clé. Déployer le collecteur avec le déclencheur de collecte quotidien et le binding D1 `DB`.
3. Configurer le binding D1 `SALES_DB` du Worker d'interface sur cette même base. Cette liaison est facultative pour les déploiements sans collecteur. Éviter les identifiants d'environnement dans le code applicatif.
4. Vérifier dans D1 `paid_sale_scans` et `paid_market_sales`, puis ouvrir le Radar et comparer la variante, le nombre de ventes et le prix. En cas d'échec ou de résultat vide, inspecter le passage suivant avant de conclure à une couverture réelle.

Sans activation, la prévisualisation continue d'afficher l'historique déjà documenté. Les pages d'enchères source peuvent refuser la lecture ou évoluer. Les tests locaux simulent les réponses externes et vérifient le comportement avec SQLite.
