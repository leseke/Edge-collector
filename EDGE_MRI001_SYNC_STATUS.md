# EDGE MRI-001 — baseline importée et vérifiée

Import du 21 octobre 2026, exclusivement sur `edge/mri-001-baseline`.

Source : `/EDGE/Backups/edge-mri-001-complet-2026-10-21.zip`.
Manifeste : `edge-mri-001-manifest-2026-10-21.json`.
SHA-256 archive : `5b93d0dfaeae44449cccf3c5f80fa66250e4800f2f8527f3b0fe3c7a37c4eef4`.

- 151/151 fichiers conformes au manifeste SHA-256 ; aucun manquant, supplémentaire ou divergent dans l'archive.
- Par rapport au parent b2c8a676efeb4ad2644aaa3ce487c0e50c81c4b8 : 121 ajouts, 10 modifications, 20 fichiers identiques.
- Ce marqueur préexistant est actualisé séparément ; aucun fichier de l'archive n'est altéré.
- Recherche de clés privées, jetons connus, identifiants littéraux et fichiers sensibles : aucun secret détecté. Contrôle du projet `python -m tools.check_public_files .` : 49 fichiers contrôlés, 0 problème. Ces contrôles ne garantissent pas l'absence de tout secret possible.
- Python 3.12, dépendances de requirements.txt installées ; `python -m tools.run_tests_offline` : 312 tests, OK, 1 ignoré, 0 tentative réseau. Premier passage incomplet avant installation de requests ; relance complète réussie.
- Les trois workflows importés sont uniquement manuels ; aucun workflow lancé.
- Aucun déploiement, aucune modification de main, aucune fusion de PR.

Les limites fonctionnelles de MRI-001 restent celles de `EDGE_MARKET_REACTION.md`. La réussite des tests hors ligne ne valide pas les fournisseurs en production.
