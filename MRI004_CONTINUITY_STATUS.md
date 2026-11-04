

## MRI-004.17 — Protocole durable v2 consolidé (documentation uniquement)

- Document de référence créé : `MRI004_17_PROTOCOL_V2.md`.
- Commit documentaire : `64ea778b58aeb17e15bfecff6375d5ce8484c50e` (HEAD vérifié sur la branche `edge/mri-004-continuity-notification-contract`).
- Le document consolide les contrats 004.17-A à G : canonicalisation JSON, UTC canonique, identité et hash des événements, séquences et hash chain, transport create-only, retries/readback, restauration sur snapshot épinglé, inventaire complet, vérification des blobs, audit historique depuis une ancre de genèse indépendante, statuts de confiance et tests d'acceptation.
- Décision v2 : chemin `runs/<run_key>/<attempt>/<sequence>.json`, qui remplace pour les futures écritures v2 le chemin par date proposé en MRI-004.16. Les événements immuables sont l'unique source de vérité ; tout manifeste reste reconstructible.
- Compatibilité : lecture v1 possible en mode historique, mais v1 ne peut pas obtenir `CONTINUITY_VERIFIED`. v2 est le seul format d'écriture futur.
- Le snapshot Git final ne suffit pas à prouver l'absence de suppressions antérieures. Une continuité vérifiée exige aussi un audit linéaire des commits depuis un SHA de genèse conservé indépendamment. Les commits de merge sont refusés par le protocole initial.
- **État réel :** aucun code v2 n'a été intégré ; aucun test v2 n'a été exécuté ; aucun backend privé n'est provisionné ; aucun scheduler n'est activé. La CI de 509 tests (508 réussis, 1 ignoré) reste celle du dernier commit de code testé `d8855adc44332a9a5053dd0a02b26b1686f63d7d`, run `41694975268`. Le commit `64ea778` est documentaire et n'est pas présenté comme un commit de code testé.
- Vérification GitHub du 4 novembre 2026 : la branche de travail est actuellement signalée `protected=false`. Il faudra activer des protections adaptées avant de lui confier une fonction d'archive durable. Cela ne constitue pas une protection du journal privé cible.
- La branche `main` n'a pas été modifiée. Aucun merge, rebase, force-push, secret, appel fournisseur, dépense API ou notification réelle n'a été effectué.
