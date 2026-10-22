# EDGE MRI-002 — Validation indépendante (22 octobre 2026)

Branche : `edge/mri-002-actor-intelligence`; base MRI-001 : `37e1dc23032a8838b201ce7f06680afbcd8b1ea2`.

## Résultats reproduits
- Suite ciblée : `python -m unittest tests.test_actor_intelligence tests.test_market_reaction -q` → **17 tests réussis, 0 échec**.
- Premier essai intégral : 313 tests découverts, 1 ignoré, 1 erreur d'import `actor_intelligence` dans une copie locale historique des tests. Le test présent sur GitHub importe correctement `intelligence.actor_intelligence`. Cet essai n'est **pas** une validation de la branche.
- Deux reprises de la suite intégrale après correction du montage local ont expiré avant une conclusion exploitable. **Suite complète non validée pour MRI-002**.
- Aucun accès API ou dépense payante n'a été volontairement déclenché pour ces essais.

## Portée
Les tests ciblés utilisent des événements fictifs datés. Ils prouvent le filtrage temporel et la séparation des décisions, **pas une capacité d'anticipation réelle**. Aucun replay sur événements historiques de marché authentifiés n'a encore été accepté.

## Conditions avant MRI-003 / production
1. Exécuter la suite complète jusqu'au bout sur un environnement stable et recueillir le log final.
2. Vérifier la divulgation sur tous les fichiers de la branche, avec périmètre explicite.
3. Constituer des cas historiques datés avec visibilité « connue au temps T » et un contrôle de fuite temporelle.
4. Évaluer séparément la qualité des hypothèses et les réponses réelles ultérieures, sans déclarer une causalité.
5. Conserver l'accès aux modèles réels et les opérations payantes désactivés.

Aucune modification de `main` ni déploiement.
