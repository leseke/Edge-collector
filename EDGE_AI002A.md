# AI-002A — Premier agent d'intelligence hors ligne

Question → plan → inventaire autorisé → agent → **conformité** → ingestion AI-001.1 → validation → stockage → dossier.
Aucun réseau, aucun modèle, aucune dépense. AI-001.1 n'est pas modifié.

## Diagnostic initial
L'ingestion AI-001.1 bloquait les chiffres *structurés*, mais acceptait (démontré avant ce lot) :
un chiffre inventé dans le texte, une citation attribuée à la mauvaise source, une instruction malveillante recopiée, un graphique demandé sur un dataset vide. AI-002A ajoute une couche de conformité **en amont**, sans toucher à l'ingestion.

## Composants ajoutés (`intelligence/`)
| Module | Rôle |
|---|---|
| `corpus.py` | Corpus **autorisé** (`edge.corpus.v1`) : sources, datasets, extraits. Validé à l'entrée par le validateur EDGE ; refus systématique (nombre non fini, devise inconnue, source inexistante, simulation mal déclarée, clé privée…). Le texte des extraits est une donnée non fiable. |
| `planner.py` | Question → corpus → sous-questions. `OK`, `AMBIGUOUS` (marché non identifiable : on demande une précision), `NO_DATA`, `INVALID`. Aucune devinette. |
| `offline_agent.py` | Agent déterministe au contrat AI-001 : faits = extraits recopiés à l'identique avec leur source ; contradictions ; inconnues ; graphiques par identifiant ; aucun chiffre, aucune décision, aucun avis favorable. **Remplaçable par un modèle sans toucher aux validateurs.** |
| `compliance.py` | Rejet en bloc si : source inconnue, citation incohérente ou altérée, chiffre absent des sources citées, instruction suspecte (contenu tiers), graphique sans données / dataset inconnu / unités mêlées, champ interdit (dont toute décision). |
| `inquiry.py` | Orchestrateur ; décision EDGE fournie par EDGE (`NOT_EVALUATED`) ; rapport au mieux `partial` ; nouvelle exécution = **nouvelle version** ; fournisseur payant ⇒ verrou R4.2 (refusé sans garde, avant tout appel). `refresh_due()` : conditions d'actualisation objectives. |
| `dossier.py` | Dossier d'enquête immuable : plan, inventaire, extraits écartés (motif seulement, texte non republié), contradictions, inconnues, conformité, actualité, conditions d'actualisation. |
| `ask.py` | Point d'entrée utilisateur. Écrit par défaut dans `private/intelligence_preview` (non publié). |

## Utilisation
```
python -m intelligence.ask "Analyse l'évolution de Pokémon en Chine, l'intérêt international pour ses cartes et les opportunités de revente en France."
python -m intelligence.ask "..." --store data/intelligence     # publication explicite pour le dashboard
```

## Conditions objectives d'actualisation (dossier)
`data_age` (données plus anciennes que la politique de fraîcheur) · `corpus_changed` (empreinte du corpus différente) · `unanswered_subquestion` (une sous-question sans réponse devient documentée).

## Exemple complet
`intelligence/examples/ai002a/` : rapport `partial`, simulé, 3 sous-questions (2 documentées, revente en France inconnue), contradiction `cn_sales_trend` visible des deux côtés, extrait malveillant `ext_c2` écarté, 2 graphiques issus uniquement des données du corpus, décision EDGE `NOT_EVALUATED`.
Second domaine (générique) : `intelligence/corpus/velos_nl_demo.json` (vélos cargo d'occasion, Pays-Bas).

## Limites
- Corpus de démonstration **fictifs** : aucune donnée réelle n'a été archivée ni vérifiée dans ce lot.
- Détection d'injection par motifs : efficace contre les formes testées, pas exhaustive face à un texte adverse inventif ; la défense principale reste structurelle (le texte tiers n'est jamais exécuté, la décision ne vient jamais de l'agent, toute sortie est contrôlée).
- Planificateur par mots-clés : une question formulée sans les termes du corpus peut tomber en `NO_DATA` ou `AMBIGUOUS` (comportement prudent voulu).
- La contrainte « faits = extraits recopiés à l'identique » est stricte pour un futur modèle : AI-002B devra décider d'une règle de citation (extrait exact + reformulation séparée).

## Retour arrière
`git revert <commit AI-002A>` : supprime les modules, corpus, exemple, tests et cette documentation. AI-001.1 n'ayant pas été modifié, rien d'autre n'est affecté. Rapports éventuellement publiés : supprimer leurs entrées n'est pas possible (historique immuable) — supprimer `data/intelligence/` entier si nécessaire.
