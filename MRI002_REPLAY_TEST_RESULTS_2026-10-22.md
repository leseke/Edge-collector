# MRI-002 — Validation des tests de rejeu (22 octobre 2026)

## Résultat
Copie de test reconstruite depuis l'archive `edge-mri-001-complet.zip`, augmentée des modules et tests MRI-002 publiés sur GitHub. **Ce n'est pas un workflow GitHub Actions ni un checkout Git distant comparé octet par octet.**

- `python -m unittest tests.test_blind_replay -v` : **5 tests / 5 PASS**.
- `python -m tools.run_tests_offline` sur la copie reconstruite avec les suites Actor Intelligence + Blind Replay : **325 tests exécutés, OK (skipped=1), 0 échec**, environ 12,4 s, **0 tentative réseau**.
- `python -m tools.check_public_files --tracked` : **154 fichiers contrôlés, 0 problème**. Repli sur l'arborescence filtrée par `.gitignore` puisque les métadonnées Git sont absentes de la copie ZIP.
- Ignoré : scénario TCGdex dépendant d'une réponse réelle enregistrée qui manque à l'archive.

## Contrôles des cinq tests de rejeu
1. N'inclut pas une observation connue après la date T0.
2. Retourne `PENDING` avant échéance.
3. Refuse de réintroduire une observation connue plus tard dans une prédiction figée.
4. Détecte une modification de la thèse après scellement.
5. Refuse une preuve future comme appui d'une thèse datée T0.

## Limites d'homologation
Les données des cinq tests sont **fictives** ; elles démontrent des contraintes de contrôle et non une anticipation rentable ou causale. Les dossiers Pokémon Chine 2022 et LEGO 10365 2025 sont des **candidats de recherche**, pas des historiques d'observations EDGE authentifiés. Les fichiers MRI-002 ont été reconstitués à partir du contenu publié et ne font pas l'objet d'une validation d'identité binaire avec les blobs GitHub dans cet essai ; l'état exact du commit GitHub reste à vérifier dans un checkout indépendant ou CI.

Aucun déploiement, aucun BUY automatique, aucune modification de `main`.
