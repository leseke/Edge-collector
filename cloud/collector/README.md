# EDGE — collecteur Cloudflare expérimental (non déployé)

Ce dossier prépare un **Worker distinct** de l'interface Next.js déjà en ligne.
Le collecteur n'est **ni actif ni planifié**. Aucun cron, D1 ou abonnement
n'est créé par ces commits.

## État du prototype

- Deux identifiants de cartes TCGdex sont utilisés comme sondes techniques.
  Ils ne constituent pas une liste de recommandations ou un radar multi-TCG.
- À chaque exécution future, une ligne immuable sera écrite par réponse
  exploitable dans D1, avec heure, identifiant, URL, prix agrégé éventuel,
  catégorie AGGREGATE, disponibilité UNKNOWN et SHA-256 du corps.
- Une collecte échouée est enregistrée comme échec du run ; les erreurs
  individuelles ne sont pas encore historisées en table dédiée.
- Le corps source complet n'est pas archivé : un hash seul ne suffit pas à
  rejouer ni auditer intégralement les données. Il faudra un stockage R2
  ou un autre archivage des preuves avant une exploitation décisionnelle.
- Le code TypeScript du Worker n'est pas encore couvert par un typecheck
  Cloudflare indépendant, ni par des tests d'intégration D1.
- Aucune vente conclue n'est inférée de prix Cardmarket agrégés.
- Pas d'API payante, d'Ollama cloud, ni d'exécution automatique.

## Activation ultérieure — validation préalable obligatoire

1. Tester et typer le Worker avec les types Cloudflare et une D1 locale.
2. Vérifier les identifiants, formats TCGdex, règles d'usage, réponses réelles
   et limites réseau. Corriger les cibles invalides avant activation.
3. Créer explicitement une D1, appliquer `schema.sql` et remplacer l'ID
   fictif dans une copie locale de `wrangler.example.jsonc`.
4. Vérifier le fonctionnement et les coûts/quota du plan utilisé.
5. Déployer séparément, puis activer volontairement un cron via
   `triggers.crons`. Ne jamais exposer de déclencheur public de collecte.
6. Ajouter historique des erreurs, preuve brute, déduplication, quotas,
   freshness et lecture sécurisée des résultats dans EDGE.

Le fichier exemple contient une valeur factice ; **ne pas** l'utiliser
tel quel pour un déploiement. Ne jamais mettre de secret dans GitHub.
