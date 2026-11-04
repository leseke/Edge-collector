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

## MRI-004.5 — Reconstruction multi-runs

- `intelligence/reconstruct_continuity.py` : vérification par rejeu du journal d'exécution restauré et reconstruction des fenêtres planifiées à partir de preuves source séparées.
- `tests/test_reconstruct_continuity.py` : scénarios multi-runs, fenêtre manquée, absence de réaction, échec source, run interrompu, run terminé sans preuve source, historique corrompu et résultats non rattachés à un run vérifié.
- Règle de prudence : fenêtre sans exécution = `MISSED`; exécution présente sans preuve source = `UNKNOWN`; aucune assimilation du heartbeat à une observation.
- Les ratios d'observation et de tentative sont séparés et masqués dès qu'une fenêtre reste `UNKNOWN`. Une erreur source produit `DEGRADED`, pas `CONTINUOUS`.
- Le simulateur accepte maintenant les événements `SOURCE_RESULT` et la reconstruction peut extraire les preuves directement du journal restauré ; `storage.py` et le collecteur réel ne les écrivent pas encore. Le scheduler et l'émission de preuves source par le collecteur restent à intégrer. Le résultat actuel est un modèle hors ligne alimenté par des événements synthétiques.
- CI : résultat des nouveaux commits à confirmer ; aucun total de tests n'est revendiqué à ce stade.

## MRI-004.6 — Granularité par source

- `intelligence/reconstruct_continuity.py` accepte maintenant plusieurs résultats source pour une même fenêtre, avec une liste indépendante `expected_sources` fournie par le scheduler.
- Agrégation testée : observation, absence de réaction, échec total, échec partiel (`DEGRADED`), source attendue manquante (`UNKNOWN`) et fenêtre sans exécution (`MISSED`).
- Les détails de chaque source restent visibles dans le résultat reconstruit ; les métriques distinguent couverture d'observation et couverture de tentative.
- 14 tests dédiés dans `tests/test_reconstruct_continuity.py` et 12 tests dans `tests/test_remote_journal_simulator.py` (26 tests ciblés au total), dont une restauration effective du journal depuis le simulateur et un cas de runs concurrents ambigus, ainsi que des événements source intégrés au journal simulé (écrits, CI à confirmer).
- Toujours pas d'émission de preuves source par le collecteur réel : les données sont injectées dans le modèle de reconstruction hors ligne. `collect.run()` écrit encore `scheduled_at=None`; le scheduler et le branchement réel restent à faire.
- Vérification GitHub du commit de tests : aucun statut de test GitHub Actions n'est remonté par l'API de statut consultée ; le déploiement Vercel du commit de test échoue avec `missing_pages_app` (build Next.js sans application Pages détectée) ; aucun run GitHub Actions de tests n'est visible via les statuts/endpoint PR consultés, ce qui ne permet pas de conclure sur les tests Python. Aucun test n'est déclaré vert sans log explicite.

## MRI-004.7 — Journal source-level SQLite

- `storage.py` accepte maintenant les événements `SOURCE_RESULT` dans le journal SQLite local, avec liste blanche stricte (`window_id`, `source_id`, `outcome`).
- Le cycle est contrôlé dans une transaction `BEGIN IMMEDIATE` : un résultat source exige un STARTED unique et doit précéder FINISHED.
- Plusieurs sources peuvent être enregistrées pour un même run/fenêtre. Une répétition identique est idempotente ; une répétition avec contenu différent est rejetée.
- Les issues inconnues, les identifiants vides et les champs privés supplémentaires sont rejetés.
- `tests/test_run_journal.py` couvre les nouveaux cas SQLite ; `tests/test_reconstruct_continuity.py` couvre aussi le rejet d'un événement source malformé avant extraction de son payload.
- `reconstruct_continuity.py` valide maintenant l'intégralité de l'historique avant de lire les champs internes des événements source, évitant une extraction prématurée susceptible de lever une erreur de clé non contrôlée.
- Le collecteur réel n'émet **toujours pas** `SOURCE_RESULT` : aucune fenêtre planifiée fiable n'est disponible (`scheduled_at=None`) et aucun scheduler ne définit `window_id` ou la liste `expected_sources`. Les écrire aujourd'hui reviendrait à inventer une preuve de planification. Cette étape ajoute donc le contrat de stockage, sans attribuer de faux résultats aux sources.
- Les états `NO_REACTION_OBSERVED` et `SOURCE_FAILED` ne sont pas encore dérivés automatiquement des appels fournisseurs. Une réponse vide n'est pas assimilée à une absence de réaction ; une source désactivée ou non appelée ne devient pas un échec.
- Tests ciblés présents après cette étape : 15 tests du journal SQLite, 15 tests de reconstruction, 12 tests du simulateur (42 ciblés). **Ils ne sont pas déclarés réussis : aucune exécution Python ni CI GitHub Actions confirmée pour ces derniers commits.**
- Le statut combiné GitHub consulté sur le commit de tests ne remonte que le contrôle Vercel, en attente ; il ne donne pas le résultat du workflow Python. Le déploiement Vercel reste indépendant de ces tests.
- Aucun scheduler, backend distant, secret, appel payant, notification réelle ou changement de `main` n'a été activé.
## Validation MRI-004.7 — CI confirmé

- Après correction des deux assertions qui comparaient un ratio arrondi (`0.6667`) à la fraction exacte (`2/3`), le workflow hors ligne a réussi.
- Commit testé : `81a4fdf645fd610fd51688d91a58e2b3c46f2b42`.
- GitHub Actions run `41660626186` : **success** — 389 tests exécutés, 1 ignoré, 0 échec. Journal : https://github.com/leseke/Edge-collector/actions/runs/41660626186
- Cette réussite couvre la suite complète au commit testé, y compris les nouveaux tests SQLite, les tests de reconstruction et le test de validation du payload source malformé. Elle ne signifie pas que le collecteur réel émet déjà des événements `SOURCE_RESULT`.
- Le document lui-même est mis à jour après le commit testé ; le changement documentaire ne modifie pas le code testé.
## Extension du contrat applicatif

- `intelligence/run_journal.py` expose maintenant `source_result()` dans le protocole `RunJournal` et dans l'adaptateur `SQLiteRunJournal` ; le test de délégation correspondant est ajouté.
- Cette méthode délègue uniquement à la liste blanche SQLite déjà testée. Elle n'est pas appelée depuis `collect.py` tant que le collecteur ne reçoit pas une fenêtre planifiée vérifiable.
- La dernière suite complète confirmée reste 389 tests réussis, 1 ignoré au commit `81a4fdf`. Le nouvel ajout de l'adaptateur et son test sont en cours de validation GitHub Actions (run `41660866058`) ; ne pas étendre la mention de réussite au commit suivant avant son résultat.
## Validation finale de l'adaptateur source

- Commit testé : `bc945d2e4050105db2822167b37b834fba1651ac`.
- GitHub Actions run `41660866058` : **success** — 390 tests exécutés, 1 ignoré, 0 échec. Journal : https://github.com/leseke/Edge-collector/actions/runs/41660866058
- Le test ajouté valide la délégation `SQLiteRunJournal.source_result()` vers le stockage SQLite ; les tests couvrent aussi l'ordre STARTED/SOURCE_RESULT/FINISHED, plusieurs sources, l'idempotence, le rejet des changements de contenu et des champs privés.
- Cette validation ne couvre pas encore une collecte réelle avec fenêtre planifiée : `collect.py` n'émet pas `SOURCE_RESULT` tant qu'aucun scheduler fiable ne fournit les identifiants de fenêtre et les sources attendues.

## MRI-004.14-A — Dispatch uniforme des connecteurs

- `connectors/status_adapters.py` expose désormais `fetch_source_with_status(provider, item)`, point d'entrée uniforme vers les adaptateurs de statut des cinq familles actuellement utilisées : eBay, Cardmarket, Google Trends, Reddit et Scavio.
- Le contrat de retour est strict : `(snapshot | None, ConnectorResult)`. Le snapshot historique reste inchangé ; le résultat de statut doit être une instance valide de `ConnectorResult`.
- Les fournisseurs inconnus, champs de requête obligatoires absents, formes de retour incorrectes et résultats non conformes sont rejetés explicitement.
- Les cas `None` ambigus des connecteurs historiques eBay, Cardmarket, Trends et Reddit restent `UNKNOWN`. Ils ne deviennent pas artificiellement `NO_REACTION_OBSERVED`. Seul l'adaptateur Scavio, qui demande explicitement les erreurs et distingue une réponse Shopping vide réussie, peut déclarer `NO_REACTION_OBSERVED`.
- `NOT_SCHEDULED` n'est pas fabriqué par le dispatcher : l'absence de programmation reste une décision du plan de sources, en amont de tout appel.
- `tests/test_source_status_dispatch.py` couvre les cinq dispatchs, la conservation du snapshot et du statut, le rejet d'un provider inconnu, les paramètres requis, et la conservation de `UNKNOWN` / `SOURCE_FAILED`.
- Validation CI exacte : commit `fcefc4f0bc630ab8a265aa74f44bcb0fa71fd0bc`, GitHub Actions run `41684437278` : **success**, 495 tests exécutés, 494 réussis, 1 ignoré, 0 échec. Journal : https://github.com/leseke/Edge-collector/actions/runs/41684437278
- Limite explicite : ce dispatcher n'est pas encore appelé depuis `collect.py`. La CI teste les appels avec mocks ; aucun connecteur externe n'a été appelé et aucune fenêtre planifiée n'a été créée. Les étapes 004.14-B à 004.14-E restent à réaliser.
- Aucun changement sur `main`, aucun scheduler réel, aucun appel payant, aucune notification réelle et aucun nouveau secret.


## MRI-004.14-B — Injection explicite du contexte planifié

- `intelligence/scheduled_run_context.py` expose `validate_scheduled_invocation()` : avant toute écriture, la fonction vérifie le type du contexte, l'identité exacte du run et de sa tentative, l'unicité de la fenêtre, l'instant UTC et l'ensemble exact des sources attendues.
- `collect.run()` accepte maintenant deux arguments facultatifs : `scheduled_context` et `expected_windows`. Ils doivent être fournis ensemble. Un contexte incohérent est rejeté avant `init_db()` et avant toute écriture STARTED.
- Sans contexte explicite, le chemin manuel/local historique est conservé : `scheduled_at=None`. L'heure de démarrage du processus et les métadonnées GitHub ne sont jamais utilisées pour deviner une fenêtre.
- Avec contexte vérifié, STARTED reçoit l'instant explicite fourni et le déclencheur logique `schedule`. Cette interface n'active aucun scheduler et n'est pas appelée par le workflow existant.
- Tests : cas valide avec tentative GitHub, identité de run incohérente, fenêtre absente, instant différent, sources attendues modifiées, et compatibilité du chemin manuel.
- Validation CI du commit `087c6bb566e7b3adfd08c1491e4541c792aade90`, run `41684991658` : **success**, 501 tests exécutés, 500 réussis, 1 ignoré, 0 échec. Journal : https://github.com/leseke/Edge-collector/actions/runs/41684991658
- Le changement de docstring de `intelligence/scheduled_run_context.py` a ensuite été fait sur le commit `8e1096b5ff3fd59ac46767fa9b5a5820b54af633` ; la CI de ce HEAD doit être vérifiée séparément avant de considérer ce dernier commit validé.
- Limite : le collecteur n'émet pas encore `SOURCE_RESULT` et ne reconstruit pas encore le rapport de continuité. C'est le périmètre de 004.14-C/D. Aucun scheduler, appel externe ou changement de `main`.

## MRI-004.14-C — Raccordement des résultats source au collecteur

- Le chemin planifié de `collect.run()` utilise désormais `SQLiteContinuityJournal` pour écrire STARTED, les résultats source et FINISHED. Le chemin manuel conserve son cycle historique et n'émet aucun `SOURCE_RESULT`.
- Le collecteur utilise le dispatcher de statut pour chaque contrôle planifié de la watchlist principale (eBay/Cardmarket), Trends, Reddit et Scavio. Chaque résultat exécuté est rattaché à l'identifiant de contrôle attendu dans la fenêtre vérifiée.
- Les statuts `OBSERVED`, `NO_REACTION_OBSERVED` et `SOURCE_FAILED` sont transmis au journal via la liste blanche SQLite. Les cas `UNKNOWN` ne sont pas enregistrés comme résultat ; un contrôle désactivé/non exécuté n'est pas transformé en échec et reste sans preuve.
- Les échecs enregistrés ne conservent que le type d'exception, jamais le message fournisseur. Les snapshots historiques et la sortie radar restent inchangés.
- Tests ajoutés : transmission du résultat planifié au journal, statut d'échec expurgé, conservation du chemin manuel. Les tests SQLite existants couvrent l'ordre STARTED/SOURCE_RESULT/FINISHED, l'idempotence, les doublons contradictoires, l'absence de réaction et les erreurs.
- Validation CI : commit `3592dbc7900c092fcdbd18cfac96ac643b0e283c`, run `41686464879` : **success**, 504 tests exécutés, 1 ignoré, 0 échec. Journal : https://github.com/leseke/Edge-collector/actions/runs/41686464879
- Le workflow de tests surveille maintenant aussi `connectors/**`, afin que les changements d'adaptateurs déclenchent la suite hors ligne.
- Limites : aucun scheduler n'est activé ; les fenêtres et sources attendues doivent toujours être injectées explicitement. Le workflow de collecte actuel continue d'exécuter `diagnose_scavio.py`, pas `collect.py`. Le journal SQLite est local au runner et ne constitue pas encore une persistance durable multi-exécutions. Les tests utilisent des mocks/offline et ne valident pas la disponibilité réelle des fournisseurs.
- Aucun appel fournisseur, dépense, notification réelle, secret supplémentaire, changement de `main`, merge ou rebase n'a été effectué.

## MRI-004.15 — Reconstruction liée aux preuves et lecture SQLite locale

- `verify_run_history()` contrôle désormais l'ordre chronologique des événements par tentative et refuse les horodatages non monotones. Un STARTED planifié doit porter `trigger=schedule` et un `scheduled_at` explicite ; un déclencheur manuel ne peut pas revendiquer cet instant.
- La reconstruction tire les preuves exclusivement des événements `SOURCE_RESULT` présents dans le journal vérifié. Le paramètre historique `source_outcomes` reste accepté uniquement s'il reproduit exactement les événements enregistrés ; il ne peut plus ajouter, remplacer ou inventer une observation.
- La borne `as_of` s'applique aussi à FINISHED : une exécution terminée après l'instant de référence reste `UNKNOWN`, même si les résultats source sont déjà présents.
- `storage.list_all_run_events()` restitue le flux SQLite complet en ordre d'insertion. `SQLiteContinuityJournal.read_history()` le convertit au format de rejeu. Le stockage identifie déjà chaque tentative par un `run_id` unique ; le champ technique `attempt` du flux reconstruit est normalisé à 1 pour chaque `run_id`.
- `build_local_sqlite_continuity_report()` permet de reconstruire un rapport directement depuis l'adaptateur SQLite. Par prudence, il conserve les observations positives effectivement enregistrées, mais rétrograde les fenêtres sans événement de `MISSED` vers `UNKNOWN`, masque les ratios et indique `journal_status=DEGRADED` (ou `UNKNOWN` si le journal est vide), car le SQLite local au runner ne prouve pas l'exhaustivité de l'historique.
- Tests ajoutés/renforcés : résultat externe falsifié, résultats dupliqués, exécution manuelle revendiquant une fenêtre planifiée, horodatages non monotones, FINISHED postérieur à `as_of`, lecture multi-événements SQLite et rapport local prudent.
- Validation CI : commit testé `d8855adc44332a9a5053dd0a02b26b1686f63d7d`, run `41694975268` : **success**, 509 tests exécutés, 508 réussis, 1 ignoré, 0 échec. Journal : https://github.com/leseke/Edge-collector/actions/runs/41694975268
- Limite non levée : ce rapport local n'est pas une persistance durable. Tant que le journal n'est pas conservé entre runners et que son exhaustivité n'est pas prouvée, il ne peut annoncer une continuité globale ni des fenêtres manquées fiables. Aucun scheduler ni appel externe n'est activé.


## MRI-004.16 — Architecture de persistance durable

- Nouveau document `MRI004_16_DURABLE_PERSISTENCE.md` : décision MVP en faveur d'un dépôt GitHub privé dédié, distinct du dépôt applicatif public.
- Format retenu : un fichier JSON immuable par événement, partitionné par date UTC. Cela évite le verrou global d'un fichier JSONL partagé ; les collisions d'identité sont traitées par relecture et comparaison stricte.
- Le manifeste reste reconstructible et non autoritaire. Une restauration ne peut être déclarée vérifiée qu'après pagination complète et validation de l'ensemble des événements.
- Matrice d'acceptation définie pour les retries ambigus, les écritures concurrentes, les collisions contradictoires, les pannes, la pagination incomplète, les événements malformés et la restauration depuis un environnement vierge.
- Sécurité : aucun journal opérationnel dans le dépôt public ; aucune donnée financière/personnelle ou payload fournisseur ; aucun secret dans le code ou la conversation.
- **Limite bloquante assumée :** aucun dépôt privé ni credential n'est provisionné. L'adaptateur réel n'est donc pas activé et SQLite reste non durable entre runners. Cette livraison est une décision d'architecture documentée, pas une persistance opérationnelle.
- Prochaine dépendance : création manuelle du dépôt privé et configuration d'une identité d'écriture limitée à ce dépôt. Communiquer uniquement `owner/repository`, jamais le jeton.


## MRI-004.17 — Protocole durable v2 consolidé (documentation uniquement)

- Document de référence créé : `MRI004_17_PROTOCOL_V2.md`.
- Commit documentaire du protocole : `64ea778b58aeb17e15bfecff6375d5ce8484c50e`.
- Le document consolide les contrats 004.17-A à G : canonicalisation JSON, UTC canonique, identité et hash des événements, séquences et hash chain, transport create-only, retries/readback, restauration sur snapshot épinglé, inventaire complet, vérification des blobs, audit historique depuis une ancre de genèse indépendante, statuts de confiance et tests d'acceptation.
- Décision v2 : chemin `runs/<run_key>/<attempt>/<sequence>.json`, qui remplace pour les futures écritures v2 le chemin par date proposé en MRI-004.16. Les événements immuables sont l'unique source de vérité ; tout manifeste reste reconstructible.
- Compatibilité : lecture v1 possible en mode historique, mais v1 ne peut pas obtenir `CONTINUITY_VERIFIED`. v2 est le seul format d'écriture futur.
- Le snapshot Git final ne suffit pas à prouver l'absence de suppressions antérieures. Une continuité vérifiée exige aussi un audit linéaire des commits depuis un SHA de genèse conservé indépendamment. Les commits de merge sont refusés par le protocole initial.
- **État réel :** aucun code v2 n'a été intégré ; aucun test v2 n'a été exécuté ; aucun backend privé n'est provisionné ; aucun scheduler n'est activé. La CI de 509 tests (508 réussis, 1 ignoré) reste celle du dernier commit de code testé `d8855adc44332a9a5053dd0a02b26b1686f63d7d`, run `41694975268`. Le commit `64ea778` est documentaire et n'est pas présenté comme un commit de code testé.
- Vérification GitHub du 4 novembre 2026 : la branche de travail est actuellement signalée `protected=false`. Il faudra activer des protections adaptées avant de lui confier une fonction d'archive durable. Cela ne constitue pas une protection du journal privé cible.
- La branche `main` n'a pas été modifiée. Aucun merge, rebase, force-push, secret, appel fournisseur, dépense API ou notification réelle n'a été effectué.
