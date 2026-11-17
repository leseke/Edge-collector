# EDGE — Mise en service D1 (séparée de l'application publique)

**État :** guide d'exécution, pas une preuve de provisionnement. Aucun déploiement ni cron n'est déclenché par ce document. Les commandes distantes ci-dessous requièrent l'autorisation du propriétaire du compte Cloudflare.

## 1. Préparer localement (sans compte ni frais)

À la racine du dépôt :

```sh
npm install --no-audit --no-fund
python3 -m unittest discover -s cloud/collector/test -p 'test_*.py' -v
node --test cloud/collector/test/*.test.mjs
npx tsc --project cloud/collector/tsconfig.json
```

Le test réseau volontaire, sans écriture : `node cloud/collector/test/live-source-probe.mjs`.
Vérifier les conditions d'utilisation et les limites de la source avant de planifier des requêtes.

## 2. Provisionner D1 (action explicite du propriétaire)

Dans Cloudflare Dashboard → Storage & databases → D1 → Create database,
créer `edge-tcg-history`. Consulter les limites du plan avant confirmation.
Récupérer le **database ID** (identifiant, pas jeton d'authentification).

Depuis une session Wrangler authentifiée et autorisée :

```sh
npx wrangler d1 create edge-tcg-history
```

**Choisir une seule méthode de création** (Dashboard OU CLI), pas les deux.
La commande CLI renvoie un identifiant à copier dans la configuration.
Copier `cloud/collector/wrangler.example.jsonc` vers
`cloud/collector/wrangler.jsonc` et remplacer
`REPLACE_WITH_REAL_D1_DATABASE_ID` par cet identifiant.
Ne jamais placer de jeton Cloudflare dans GitHub.

## 3. Tester le schéma avant tout déploiement

```sh
cd cloud/collector
npx wrangler d1 execute edge-tcg-history --local --config wrangler.jsonc --file schema.sql
npx wrangler d1 execute edge-tcg-history --local --config wrangler.jsonc --command "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
```

Le test `--local` ne prouve **pas** que la base distante existe ou est accessible.
Après validation explicite du propriétaire, appliquer le schéma distant :

```sh
npx wrangler d1 execute edge-tcg-history --remote --config wrangler.jsonc --file schema.sql
```

Vérifier que les tables `collection_runs`, `observations` et
`collection_errors` existent. Cette étape écrit réellement dans la base
Cloudflare et doit être autorisée.

## 4. Vérifier les sources avant déploiement

Le collecteur ne contient que deux cibles pilotes et son analyse de prix
est indicative. Ne pas activer un cron avant que le test réseau réel ait
réussi et que les règles d'utilisation de la source aient été vérifiées.
La preuve brute n'est pas archivée : la base D1 actuelle n'est **pas**
une source de transactions conclues ni une base de décision d'achat.

## 5. Déployer séparément, uniquement après accord

```sh
cd cloud/collector
npx wrangler deploy --config wrangler.jsonc
```

Aucun `triggers.crons` n'est défini : déployer ne programme pas
automatiquement les collectes. Le point HTTP public renvoie 503 et ne
déclenche pas de collecte. Ne pas ajouter de cron sans contrôle des quotas,
du coût, des erreurs et de la fiabilité des cibles.

## 6. Critères de validation

- Source réelle : réponse valide, taille et provenance contrôlées.
- D1 : un run et une observation, ou un échec explicite, persistés.
- Deuxième run : nouvelle observation distincte, sans écraser l'historique.
- Lecture : prix AGGREGATE clairement distinct des ventes conclues.
- Pas de secrets dans les commits, pas de changement de `main`.
