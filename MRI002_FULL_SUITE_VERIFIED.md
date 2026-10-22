# EDGE MRI-002 — Vérification complète reproduite (22 octobre 2026)

Branche : `edge/mri-002-actor-intelligence` (main intacte).

## Exécution indépendante
Depuis une copie de la baseline MRI-001 plus les fichiers MRI-002 :

```sh
python -m tools.run_tests_offline
python -m tools.check_public_files --tracked
```

Résultats réellement observés :
- **320 tests exécutés**, `OK (skipped=1)`, **0 échec** ; durée de la suite Python ~30,2 s.
- **0 tentative de connexion réseau** pendant les tests.
- Contrôle des fichiers publics : **152 fichiers**, **0 problème**.
- Le contrôleur public indique un **repli sur l'arborescence filtrée par .gitignore**, car la copie ZIP ne comporte pas de métadonnées Git. Il ne s'agit pas d'un contrôle de l'index Git distant.
- Un test TCGdex est volontairement ignoré faute de réponse réelle enregistrée.

Attention : les logs de tests contiennent des chaînes d'exemple simulant erreurs de collecte, capital ou clé privée ; ce sont des **tests négatifs**, non des fuites détectées sur l'arborescence publiée.

## Ce que le résultat démontre
Compatibilité automatisée MRI-001/MRI-002 sur les fichiers reconstruits localement. La reproduction du comportement prédictif sur **cas historiques réels** et l'évaluation de performance restent à faire. Aucune confiance numérique calibrée, décision d'investissement ou causalité démontrée.

Pas d'appel API payant, de déploiement ou de changement de `main`.
