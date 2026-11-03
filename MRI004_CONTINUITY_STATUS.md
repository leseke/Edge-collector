# MRI-004 — État du journal de continuité

Branche : `edge/mri-004-continuity-notification-contract`

## Réalisé

- `intelligence/continuity.py` : calcul pur des fenêtres observées/manquées.
- `tests/test_continuity.py` : tests unitaires du calcul.
- `storage.py` : table SQLite `run_event` et fonctions d'écriture/lecture du journal.
- `tests/test_run_journal.py` : tests du journal append-only, des exécutions interrompues et de l'ordre des événements.
- `tests/test_collect_heartbeat.py` : tests de l'enveloppe réelle du collecteur, du cas réussi et de l'exception sans fuite du message brut.
- `collect.py` : enveloppe de début/fin autour de l'exécution du collecteur. Un événement STARTED est écrit avant le travail ; FINISHED est écrit dans finally, y compris après exception.
- `.github/workflows/mri-tests.yml` : workflow de tests hors ligne uniquement, sans secrets ni appels fournisseurs.

## Contrat du journal

- Un run reçoit un identifiant unique, incluant le numéro de tentative GitHub Actions lorsqu'il est disponible.
- STARTED est persisté avant l'exécution métier.
- FINISHED est ajouté après succès ou exception.
- Les événements sont append-only ; aucun événement existant n'est modifié.
- Un FINISHED sans STARTED, un second STARTED ou un second FINISHED sont refusés.
- Un run interrompu brutalement avant FINISHED reste détectable via `find_unfinished_runs()`.
- Le journal n'enregistre ni montants de capital, ni clés, ni messages d'exception bruts.
- Une exécution/heartbeat n'est jamais comptée comme observation du marché.

## Statut transmis

Le collecteur renvoie désormais un état de run distinct de la qualité des données :
- `OK` : au moins une famille de données a produit un résultat et aucune source n'a échoué ;
- `PARTIAL` : au moins un résultat existe, mais une ou plusieurs sources ont échoué ;
- `EMPTY` : aucune source n'a fourni de résultat et aucune erreur source n'a été relevée ;
- `FAILED` : toutes les sources attendues ont échoué ou l'exécution a levé une exception non gérée.

Les compteurs séparent les enregistrements de collecte, les snapshots de prix produit et les lots d'offres retail. Une erreur non gérée ne prétend pas connaître le nombre de données partiellement collectées : les compteurs restent inconnus.

## Limites restantes

1. Le journal SQLite est local à l'environnement d'exécution et `storage.db` est ignoré par Git. Il ne survit donc pas à la destruction du runner GitHub Actions.
2. Le workflow `.github/workflows/collect.yml` actuel exécute `diagnose_scavio.py`, pas `collect.py`. L'instrumentation du collecteur n'est donc pas encore appelée par ce workflow.
3. Il n'existe pas encore de cadence planifiée ni de `scheduled_at` fiable ; le champ reste explicitement nul.
4. Les fenêtres attendues ne sont pas encore produites par un scheduler et reliées à ce journal.
5. La suite complète a été exécutée avec succès : 351 tests réussis, 1 test ignoré. Le dernier run GitHub Actions est vert.

## Ajustement du banc de tests

La première exécution complète a révélé trois échecs préexistants dans les tests du plafond mensuel : GitHub Actions définit automatiquement `GITHUB_ACTIONS=true`, ce qui active volontairement le refus des dépenses à plafond mensuel dans cet environnement. Les tests qui vérifient le calcul local et la concurrence ont été isolés explicitement avec `GITHUB_ACTIONS=false`, tandis que le test dédié vérifiant le refus en CI reste actif. Le code de sécurité de `investigation/spend.py` n'a pas été modifié.

## Décision de sécurité

Ne pas activer de planification nocturne et ne pas remplacer le diagnostic manuel existant. Avant la surveillance continue, il faut choisir une persistance durable du journal et mesurer les coûts/quotas des collecteurs. Aucun appel payant, publication de données, notification Telegram ou changement de `main` n'est autorisé ici.
