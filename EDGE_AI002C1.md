# EDGE AI-002C.1 — Qualité des preuves

## Périmètre
Seuls `intelligence/evidence.py`, l'attente historique de `tests/test_ai002c.py` et le nouveau `tests/test_ai002c1.py` changent. Une qualification indépendante est publiée sous `intelligence/examples/ai002c1_review/`, sans altérer les huit observations ni leur ledger append-only.

## Résultat
La divergence 1999/2022 reste non résolue : un extrait de moteur de recherche affirme explicitement « Simplified Chinese » en 1999, mais aucun périmètre complet ni preuve primaire n'est connu. Ne pas attribuer sans preuve 1999 au chinois traditionnel. `scope_reviews` documente les périmètres différents, inconnus, ou la preuve non confirmée. `contradictions` ne recueille une contradiction textuelle établie que lorsque les champs de périmètre explicites sont complets et identiques et que les deux sources sont lues directement. Les contradictions numériques existantes sont conservées, avec leurs limites historiques.

La provenance est évaluée par méthode de collecte, sans score universel et sans promotion automatique à `verified`. Les rapports antérieurs ne sont pas modifiés. L'agent n'attribue pas CASH : décision non évaluée.

## Tests
`python -m unittest tests.test_ai002c1 tests.test_ai002c -q` : 27 tests réussis. La suite complète `python -m tools.run_tests_offline` a été tentée mais dépasse le délai d'exécution de l'environnement ; ne pas la considérer comme réussie. Les six nouveaux tests n'ont pas été rejoués sur la base originale avant implémentation ; cet aspect méthodologique reste à prouver.

## Limites
La qualification sémantique est conservatrice, non une vérification de vérité. Une preuve directe peut être incorrecte. Le périmètre temporel n'est pas encore normalisé en intervalles. `scope_reviews` est additif pour compatibilité, et la reconstruction du rapport d'enquête existant n'est pas effectuée : seul le dossier de qualification est nouvellement produit.

## Retour arrière
Restaurer les deux fichiers modifiés depuis AI-002C et supprimer les deux nouveaux fichiers et cette documentation. Les journaux append-only n'ont pas été modifiés.
