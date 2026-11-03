# MRI-004 — État du premier incrément

Branche : `edge/mri-004-continuity-notification-contract`  
Base fonctionnelle : `edge/mri-003-historical-evidence-gate`

## Livré dans cette étape

- `docs/MRI-004-continuity-notification-contract.md` : contrat de continuité, de preuve et de notification utilisateur.
- `intelligence/continuity.py` : calcul pur, sans I/O ni réseau, de couverture des fenêtres attendues.
- `tests/test_continuity.py` : tests unitaires du calcul de couverture et des cas limites.

Le calcul :
- prend les horaires théoriques depuis le scheduler, sans inventer de cadence ;
- ne compte que les observations explicitement marquées comme observations de marché exploitables ;
- exclut les observations futures par rapport à `as_of` ;
- interdit qu'une capture remplisse plusieurs fenêtres ;
- distingue `UNKNOWN`, `CONTINUOUS` et `GAP` ;
- expose les fenêtres manquées, la couverture et l'âge de la dernière observation.

## Limites connues — rien n'est encore intégré au collecteur

Ce premier incrément est volontairement isolé. Il n'écrit pas encore de heartbeat, ne modifie pas `collect.py`, ne lit pas encore `storage.db` et ne déclenche aucune notification.

Le workflow `.github/workflows/collect.yml` de cette branche est manuel et exécute `diagnose_scavio.py`, pas la collecte EDGE complète. Le workflow Discovery est également manuel ; son commentaire indique explicitement que la planification attend la mesure des coûts réels.

**Ne pas ajouter de planification automatique à ce stade.** Elle pourrait augmenter les appels Scavio / Apify et consommer des quotas avant que les coûts, limites et protections soient validés.

## Validation

Les tests sont écrits mais **n'ont pas encore été exécutés dans cet incrément**. Aucune réussite de tests n'est revendiquée. Aucun workflow n'a été lancé, aucun appel fournisseur effectué, aucun déploiement réalisé et aucune modification de `main` effectuée.

## Étape suivante

1. Ajouter un journal de heartbeat append-only pour chaque exécution, y compris les échecs.
2. Instrumenter le collecteur avec un bloc de finalisation garanti (`finally`) afin qu'une interruption normale ou une exception soit visible.
3. Relier les observations existantes aux fenêtres planifiées sans confondre heartbeat et données de marché.
4. Ajouter les tests d'intégration et exécuter la suite hors réseau.
5. Mesurer les coûts et les quotas avant toute proposition de planification nocturne.
