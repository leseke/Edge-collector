# MRI-002 — Rejeu historique à l'aveugle

État : **prototype non homologué**. Les deux fichiers `intelligence/blind_replay.py` et `tests/test_blind_replay.py` sont publiés sur cette branche, avec un banc d'essai à données **fictives**. Aucun résultat d'anticipation réelle n'est revendiqué.

## Contrôle indépendant réalisé avant le nouveau lot

- `python -m tools.run_tests_offline` sur MRI-002 avant ajout du banc d'essai : **320 tests, 1 ignoré, OK, 0 tentative réseau**.
- `python -m tools.check_public_files --tracked` sur copie issue du ZIP : **152 fichiers, 0 problème**, mode de repli arborescence filtrée.

## Contrôles encore ouverts

- Exécuter `python -m unittest tests.test_blind_replay -v` ; **non encore exécuté**.
- Relancer `python -m tools.run_tests_offline` sur le commit courant ; **non encore exécuté**.
- Contrôler les secrets sur le commit courant et auditer les contenus du dépôt ; **non encore exécuté**.
- Ajouter des événements historiques authentiques avec deux dates séparées (`occurred_at`, `observed_at`) et mesurer faux positifs, faux négatifs et horizon ; aucun cas authentifié intégré.

Rien n'est fusionné dans `main`, déployé ou branché sur un fournisseur payant. Le statut du moteur de décision demeure `NOT_EVALUATED`.
