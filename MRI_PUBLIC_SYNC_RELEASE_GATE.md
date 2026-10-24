# EDGE MRI — Synchronisation publique : décision de sécurité

## Statut
- Page publique `/mri/` et `/mri/data/mri_public.json` déjà publiées sur `main`.
- La branche `edge/ui-mri-bridge-001` génère un JSON `RESEARCH_ONLY` à partir du dossier historique, et le test navigateur Chromium a réussi dans GitHub Actions.
- Publication de nouveaux dossiers sur `main` : **non automatisée**.

## Barrière rencontrée
La tentative de créer un workflow GitHub Actions avec écriture directe sur `main` a été bloquée par le contrôle de sécurité de l'outil. Aucun workflow de synchronisation automatique n'a donc été ajouté ; ne pas prétendre le contraire.

## Chemin de promotion recommandé (révisable)
1. Générer `mri_public.json` depuis un commit source explicitement approuvé (pas une branche mouvante).
2. Exécuter les tests unitaires, les contrôles de fuite et un rendu navigateur sans secrets.
3. Comparer strictement le JSON proposé avec `mri/data/mri_public.json` et ouvrir une PR ne changeant que ce fichier.
4. Faire approuver la PR par le responsable ; ne pas utiliser de token en clair, ni de push automatisé sans contrôle.
5. Après fusion autorisée, vérifier le JSON et l'affichage GitHub Pages.

## Limites fonctionnelles
Le générateur actuel est limité aux deux cas historiques autorisés ; il ne découvre pas automatiquement de nouveaux signaux et n'exécute aucun moteur LLM. Les cas demeurent `RESEARCH_ONLY`, jamais `BUY`. Les montants et journaux privés restent exclus de la sortie publique.
