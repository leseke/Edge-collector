# EDGE — migration Cloudflare Workers

## Objectif et périmètre

L'application Next.js est préparée pour être exécutée sur Cloudflare Workers avec
l'adaptateur OpenNext. Le déploiement cible est un Worker Cloudflare, pas
Cloudflare Pages : EDGE utilise l'App Router et des routes dynamiques côté serveur.

Cette migration est indépendante de Vercel. Le projet Vercel existant est
conservé comme solution de retour arrière pendant la validation ; aucune
configuration, variable, domaine ou ressource Vercel n'est modifiée ici.

## Commandes

- `npm install`
- `npm run typecheck`
- `npm run cf:build` — construit Next.js puis adapte la sortie à Workers.
- `npm run cf:preview` — construit puis lance le Worker localement avec Wrangler.
- `npm run cf:deploy` — construit puis déploie le Worker sur le compte Cloudflare connecté.

Le déploiement réel nécessite une authentification Cloudflare volontaire par
l'opérateur. Aucun jeton Cloudflare ne doit être ajouté au dépôt ou à cette
conversation.

## Architecture

- Interface Next.js : Cloudflare Workers + OpenNext.
- Fichiers statiques Next.js : assets servis par le binding Workers ASSETS.
- Dépôt et historique du code : GitHub.
- Tests : GitHub Actions, sans identifiants Cloudflare et sans déploiement automatique.
- Vercel : conservé temporairement comme secours, pas requis pour le futur hébergement.
- Compagnon Python : reste un service local sur le PC de l'utilisateur.

## Limite importante : moteur Python

Le compagnon actuel n'est pas un simple endpoint stateless. Il dépend de Python,
de SQLite, d'un stockage de fichiers persistant, de contrôles loopback et, pour
le mode IA local, d'un Ollama installé sur la machine de l'utilisateur.

Il ne peut donc pas être déplacé tel quel dans un Worker JavaScript. Le
déploiement de l'interface sur Cloudflare ne rend pas le moteur Python accessible
depuis Internet et ne transforme pas Ollama local en service cloud.

Le compagnon local demeure volontairement local et doit autoriser explicitement
l'origine exacte du site EDGE déployé. Une éventuelle version cloud du moteur
nécessitera une architecture Python distincte avec stockage transactionnel
durable, identité serveur, quotas partagés, authentification, protection des
données et contrôles de dépenses. Aucun fournisseur payant n'est activé par
cette migration.

## Contraintes du plan gratuit

Le plan Workers Free annonce notamment 100 000 requêtes par jour et 10 ms de
CPU par requête. Ce quota ne constitue pas une garantie d'usage illimité :
les pics SSR, la taille compressée du Worker, les limites de sous-requêtes et
les quotas du compte doivent être contrôlés avant mise en production.

Le build Cloudflare doit réussir en CI avant toute tentative de déploiement.
La prévisualisation Wrangler doit ensuite être testée sur les routes /, /mri
et /local, y compris les interactions et les iframes legacy.

## Sécurité et cutover

1. Valider la compilation Cloudflare et les tests hors ligne.
2. Effectuer une prévisualisation Wrangler authentifiée par l'opérateur.
3. Vérifier les routes, assets, headers, formulaires et le flux local-companion.
4. Déployer un Worker de test sur le sous-domaine workers.dev.
5. Ne connecter un domaine personnalisé qu'après validation fonctionnelle.
6. Garder Vercel disponible jusqu'à confirmation du bon fonctionnement.

Aucun changement DNS, transfert de domaine, merge de PR ou suppression de
projet Vercel n'est inclus dans la préparation du dépôt.

## Diagnostic des builds GitHub → Cloudflare

Si un ancien build Cloudflare indique `main` et installe `requirements.txt`
avant d'échouer sur `package.json` introuvable, vérifier le nom de branche
attaché **au build lui-même** : relancer cet ancien build peut reconstruire
`main`, même lorsque la branche de production est désormais la branche de
migration. Déclencher un nouveau build par un commit sur
`edge/cloudflare-migration-001`, puis vérifier le commit et la branche dans
les détails du nouveau build. Ne jamais fusionner `main` pour résoudre cela.
