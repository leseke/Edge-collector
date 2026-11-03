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
- `intelligence/run_journal.py` : interface `RunJournal` et adaptateur SQLite local.
- `intelligence/remote_journal_simulator.py` : simulateur mémoire d'un journal distant avec CAS, idempotence et retries bornés ; aucun réseau.
- `tests/test_run_journal_adapter.py` et `tests/test_remote_journal_simulator.py` : tests du contrat, des conflits concurrents, des réponses perdues, des doublons, des champs privés et des pannes.
- `MRI004_PERSISTENCE_DESIGN.md` : décision d'architecture, limites, contrat et séquence de validation.

## Contrat du journal

- Un run reçoit un identifiant unique, incluant le numéro de tentative GitHub Actions lorsqu'il est disponible.
- STARTED est persisté avant l'exécution métier.
- FINISHED est ajouté après succès ou exception.
- Les événements sont append-only ; aucun événement existant n'est modifié.
- Les écritures sont sérialisées par transaction SQLite et le payload applique une liste blanche de champs ; les clés financières privées sont refusées.
- Un FINISHED sans STARTED, un second STARTED ou un second FINISHED sont refusés.
- Un run interrompu brutalement avant FINISHED reste détectable via `find_unfinished_runs()`.
- Le journal n'enregistre ni montants de capital, ni clés, ni messages d'exception bruts.
- Une exécution/heartbeat n'est jamais comptée comme observation du marché.

## Statut transmis

Le collecteur renvoie désormais un état de run distinct de la qualité des données :
- `OK` : au moins une famille de données a produit un résultat et aucune source n'a échoué ;
- `PARTIAL` : au moins un résultat existe, mais une ou plusieurs sources ont échoué ;
- `EMPTY` : aucune source n'a fourni de résultat et aucune erreur source n'a été relevée ;
- `FAILED` : aucune observation exploitable n'a été obtenue avec au moins une erreur source, ou l'exécution a levé une exception non gérée.

Les compteurs séparent les enregistrements de collecte, les snapshots de prix produit et les lots d'offres retail. Une erreur non gérée ne prétend pas connaître le nombre de données partiellement collectées : les compteurs restent inconnus.

## Continuité en mode prudent

`assess_continuity()` exige maintenant `journal_status="VERIFIED"` pour publier des compteurs de couverture. La valeur par défaut est `UNKNOWN`. Si le journal est dégradé, inaccessible ou non vérifié, les nombres d'observations, de fenêtres manquées et le ratio de couverture restent masqués (`null`). Cela empêche un historique partiel de produire artificiellement un statut CONTINUOUS.

## Limites restantes

1. Le journal SQLite est local à l'environnement d'exécution et `storage.db` est ignoré par Git. Il ne survit donc pas à la destruction du runner GitHub Actions.
2. Le simulateur distant est uniquement un banc de test en mémoire ; il ne constitue pas une persistance durable.
3. Le workflow `.github/workflows/collect.yml` actuel exécute `diagnose_scavio.py`, pas `collect.py`. L'instrumentation du collecteur n'est donc pas encore appelée par ce workflow.
4. Il n'existe pas encore de cadence planifiée ni de `scheduled_at` fiable ; le champ reste explicitement nul.
5. Les fenêtres attendues ne sont pas encore produites par un scheduler et reliées à ce journal.
6. La base précédente de validation était de 353 tests réussis et 1 ignoré. Les nouveaux tests de l'adaptateur, du simulateur et du mode prudent ont été ajoutés ; leur résultat CI doit être confirmé avant de mettre à jour le total.

## Ajustement du banc de tests

La première exécution complète a révélé trois échecs préexistants dans les tests du plafond mensuel : GitHub Actions définit automatiquement `GITHUB_ACTIONS=true`, ce qui active volontairement le refus des dépenses à plafond mensuel dans cet environnement. Les tests qui vérifient le calcul local et la concurrence ont été isolés explicitement avec `GITHUB_ACTIONS=false`, tandis que le test dédié vérifiant le refus en CI reste actif. Le code de sécurité de `investigation/spend.py` n'a pas été modifié.

## Décision de sécurité

Ne pas activer de planification nocturne et ne pas remplacer le diagnostic manuel existant. Avant la surveillance continue, il faut connecter et valider une persistance durable du journal, tester la reconstruction multi-runs et mesurer les coûts/quotas des collecteurs. Aucun appel payant, publication de données, notification Telegram ou changement de `main` n'est autorisé ici.
