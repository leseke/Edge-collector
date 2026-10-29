# EDGE — UI MRI Bridge 001 (prévisualisation isolée)

Branche : `edge/ui-mri-bridge-001`, créée depuis `edge/mri-003-historical-evidence-gate`.

**Objectif :** préparer un format public minimal de résultats MRI consommable par GitHub Pages. **Ce lot ne déploie pas et ne remplace pas le `index.html` actuel.**

## Fichiers
- `intelligence/public_mri_export.py` : export Python avec champs strictement autorisés et états explicitement bornés, aucune inclusion de capital, BUY ou données privées. Refus des champs supplémentaires.
- `tests/test_public_mri_export.py` : six tests préparés (export valide, refus capital/décision, timezone, doublons, URLs non HTTPS).
- `preview/data/mri_public.json` : deux dossiers **RESEARCH_ONLY** illustratifs sur Pokémon Chine et LEGO. Ce n'est pas une production automatique depuis le moteur, ni une preuve de bénéfices.
- `preview/index.html` : rendu statique en DOM via `textContent` ; les valeurs du JSON ne sont pas injectées en HTML. La page ne réalise qu'un GET vers un fichier JSON public, sans API secrète.

## Fonctionnement visé
1. Les analyses sont produites hors navigateur et homologuées.
2. L'export allowlist publie uniquement les champs publics, en fichier JSON.
3. GitHub Pages ou un déploiement statique de prévisualisation sert `preview/index.html` et `preview/data/mri_public.json`.
4. La production n'est activée qu'après revue sécurité, tests, approbation humaine et configuration Pages vérifiée.

## Limitations
- Les six nouveaux tests et le rendu navigateur ne sont **pas encore exécutés** sur cette branche.
- Aucune configuration GitHub Pages n'a été changée, aucune CI lancée volontairement.
- Aucun pipeline automatisé n'invoque l'exporteur pour l'instant : **pont de contrat et prévisualisation**, pas synchronisation temps réel.
- Le JSON exemple est un dossier de recherche ; les dates de publication anciennes ne sont pas des `observed_at` historiques.
- Les montants, comptes privés, clés, recommandations financières et sorties brutes du moteur ne sont pas publiés.

## Contrôles suivants
```sh
python -m unittest tests.test_public_mri_export -v
python -m tools.run_tests_offline
python -m tools.check_public_files --tracked
```
Faire ensuite un contrôle navigateur du rendu et des états manquants, puis préparer une PR de promotion vers production seulement après homologation.
