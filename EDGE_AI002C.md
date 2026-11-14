# AI-002C — Evidence Discovery

## 1. Diagnostic préalable
Base AI-002B : 263 tests hors ligne, 0 tentative réseau. Registre : seul `tcgdex` est VERIFIED ; `openai`, `web_search` UNVERIFIED. Contrôle public sur trois périmètres distincts : fichiers suivis (126, 0 problème), arborescence complète non ignorée (126, 0 problème), fichiers ignorés (`private/`, `config.private.json`, caches) dont **aucun n'est suivi**.

## 2. Ce qui a été réellement fait — quatre catégories distinctes
| Catégorie | Contenu |
|---|---|
| **Collecte réellement exécutée** | Manuelle, le 2026-10-19, par Claude avec ses outils web (2 recherches, 1 lecture de page). Enregistrée via l'import EDGE (`collector_id: manual:claude-web-tools`). Aucun collecteur EDGE automatisé, aucun service payant. L'environnement d'exécution d'EDGE n'a pas accès à Internet. |
| **Interfaces préparées, non activées** | `PublicWebCollector` (registre `public_web` UNVERIFIED, aucun domaine autorisé) ; adaptation des observations des collecteurs existants (`from_discovery_candidate`) ; fournisseur OpenAI (toujours désactivé). |
| **Données authentiques obtenues** | 8 éléments, 7 sources distinctes (voir §4), toutes `unverified`. |
| **Éléments simulés** | Aucun dans le lot réel, le magasin réel ni le corpus réel (refusés par construction). Les corpus de démonstration AI-002A restent dans `intelligence/corpus/*.json`, **séparés** du corpus réel (`intelligence/corpus/real/`). |

## 3. Schéma `edge.evidence_item.v1` (`intelligence/evidence.py`)
Chaque élément porte : origine (`public_web` / `manual_import` / `edge_collector`), URL (https, domaine valide), éditeur, `collector_id`, méthode (`page_fetch`, `search_snippet`, `manual_entry`, `collector_api`) ; `observed_at` (avec fuseau) ; `published_at` ; `verification` (`unverified` ou `human_verified` avec trace humaine — **jamais de promotion automatique**, quel que soit l'éditeur) ; droits (`quote_only`/`summary_only`/`full`/`unknown`, citation ≤ 25 mots si restreints) ; empreinte SHA-256 du contenu ; sujet, axe, relation, clé d'affirmation et position ; nature (`fact`, `commercial_claim`, `estimate`, `opinion`) ; mesure facultative.
**Mesures distinguées** : `asking_price` (prix affiché), `retail_price` (prix public de détail), `sold_transaction` (vente conclue — **exige une preuve de transaction** ; une affirmation commerciale ou une opinion n'en prouve jamais une), `estimate`, `count`. Devise ISO 4217, valeur finie et positive, période cohérente et antérieure à l'observation, territoire.

## 4. Données authentiques — cartes Pokémon en chinois simplifié
| Axe | Élément (citation exacte, ≤ 15 mots) | Source · méthode | Nature |
|---|---|---|---|
| Disponibilité | « The set was released on October 28, 2022 » | Bulbapedia (révision 4632139) · page lue | fait (wiki communautaire) |
| Disponibilité | « …introduced in 1999 » | guide non signé · extrait | fait annoncé, **contredit** ; même texte sur un second domaine (**miroir**) |
| Prix publics | « a 5-card pack (priced at 10 yuan) » → 10 CNY, 2022 | Bulbanews · extrait | prix de détail (pas une vente) |
| Réimpressions | « …reprints of cards originally from Pokémon Card 151 » | SNKRDUNK Magazine · extrait | fait (éditeur lié à une place de marché) |
| Exclusivités | « four exclusive Art Rare variants of Pikachu » | Wargamer · extrait | fait |
| Demande intérieure | « The Simplified Chinese market grew considerably » | TCG Buyers Club · extrait | **opinion** |
| Intérêt international | titre d'annonce + 28,75 USD, 2025 | eBay.de · extrait | **affirmation commerciale**, prix affiché : la page indique « 2 verkauft » mais aussi une offre possible → prix de transaction **non confirmé**, jamais enregistré comme vente |

**Axes sans donnée** : volumes de ventes, prix réalisés, comparaison Chine–Europe, anniversaires. Aucune vente conclue documentée ; aucune preuve vérifiée par un humain. Le dossier de marché (`intelligence/examples/ai002c_real/`) le déclare explicitement (4 sous-questions sans réponse), sans aucun chiffre ajouté.

## 5. Qualification (`qualify`)
Doublons exacts (même URL, même emplacement, même contenu) ignorés à l'import ; **miroirs** (même texte, autres URL) signalés et dédupliqués dans le corpus ; **pages modifiées** (même URL et emplacement, contenu différent) : nouvelle version liée à la précédente, historique conservé ; **contradictions** d'affirmation (positions divergentes) et numériques (écart > 20 % sur une même mesure/période/territoire/devise) ; **mesures anciennes** ; **sujets insuffisants** ; contenu suspect conservé mais exclu du corpus. Le type d'affirmation à la source est reporté jusqu'au rapport (`source_claim_type`, schéma 1.3.0 facultatif) par EDGE, jamais par l'agent.

## 6. Résilience
Journal append-only rejouable (source de vérité unique), fsync par élément. Une interruption laisse au plus une ligne tronquée, ignorée et **scellée** avant toute nouvelle écriture (défaut trouvé par test : sans scellement, la ligne suivante s'y collait et était perdue). Reprise idempotente.

## 7. Commandes
```
python -m intelligence.evidence_import --batch intelligence/evidence_data/pokemon_cn_sc/batch_2026-10-19.json \
  --store intelligence/evidence_data/pokemon_cn_sc --spec intelligence/evidence_data/pokemon_cn_sc/market_spec.json \
  --corpus-out intelligence/corpus/real/pokemon_cn_sc_real.json --now 2026-10-19T12:00:00+00:00
python -m intelligence.ask "Analyse les cartes Pokémon en chinois simplifié : …" --corpus intelligence/corpus/real --store /tmp/dossier
python -m tools.run_tests_offline
```

## 8. Limites des données
- Sources **secondaires ou communautaires** (wiki, presse spécialisée, lettre d'information, place de marché) ; aucune publication officielle de The Pokémon Company n'a été lue directement.
- Six éléments viennent d'**extraits de moteur de recherche** : le texte de la page en ligne peut différer ; seule la page Bulbapedia a été lue (révision identifiée).
- Droits de réutilisation **non vérifiés** : citations courtes uniquement.
- Aucune transaction ni volume : aucune conclusion de prix réalisé ou de liquidité n'est possible.
- La collecte n'est pas reproductible automatiquement (outil web de Claude) ; l'activation d'un collecteur exige une validation des CGU par domaine.
- Le choix des sources reflète ce que deux recherches ont renvoyé : couverture partielle, non représentative.

## 9. Retour arrière
`git revert <commit AI-002C>` : supprime le module de preuves, les données collectées, le corpus réel, l'exemple et la doc ; schéma ramené à 1.2. AI-002B intact.
