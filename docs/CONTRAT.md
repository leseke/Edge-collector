# EDGE contracts — observed vs proposed

Status: **DRAFT**. Never interpret a proposed signature as a deployed endpoint.

## Existing D1 schema (verified from cloud/collector/schema.sql)
- collection_runs(run_id TEXT PK, started_at TEXT, finished_at TEXT?, status RUNNING|OK|PARTIAL|FAILED|EMPTY, attempted, succeeded, failed).
- observations(observation_id TEXT PK, run_id TEXT FK, product_id TEXT, source TEXT, observed_at TEXT, price_cents INTEGER?, currency TEXT?, availability TEXT, price_kind LISTING|AGGREGATE|COMPLETED_SALE, source_url TEXT, payload_sha256 TEXT, source_updated_at TEXT?).
- collection_errors(error_id TEXT PK, run_id TEXT FK, product_id TEXT, source_url TEXT, occurred_at TEXT, reason_code TEXT).
- Observation and error rows reject UPDATE/DELETE via triggers. One observation per (run_id, product_id); one error per (run_id, product_id). **No review_queue or investigations table is established by this schema.**

## Existing JavaScript proposal signature (verified from agent-harness/proposal.mjs)
`validateProposal(input: unknown) -> { productId: string, thesis: string, catalysts: string[], risks: string[], entryHypothesis: string, exitHypothesis: string, evidence: Evidence[], status: "PROPOSAL_REQUIRES_HUMAN_REVIEW", marketDataVerified: false, purchaseAuthorized: false }`.
Evidence: `{kind: "FACT"|"WEAK_SIGNAL"|"INFERENCE"|"BET", claim: string, sourceUrl?: string, observedAt?: string}`; FACT requires HTTPS source URL and parseable timestamp.
`reviewInvestigation(rawProposal, trustedExport, now?)` matches FACT source URL and timestamp metadata against provided D1 rows; `claimSemanticsVerified: false`, `purchaseAuthorized: false`. Invalid facts may result in `NEEDS_EVIDENCE_CORRECTION`.
`runInvestigations(trustedExport, generate, {now?,cursor?,maxProducts?})` handles at most 20 products per page, returns `processedProducts`, `remainingProducts`, `nextCursor`, `results`, `purchaseAuthorized: false`.

## Proposed TypeScript domain signatures (NOT implemented)
- `Observation`: immutable D1 observation; `price_kind` discriminates price provenance.
- `Investigation`: stable id, productId, createdAt, evidenceSnapshotRef, status.
- `Evidence`: kind, claim, optional citation metadata, independent verification state.
- `Proposal`: thesis, catalysts, risks, entryHypothesis, exitHypothesis, evidence; never an order.
- `ReviewDecision`: investigationId, reviewerId, decision APPROVE|REJECT, rationale, decidedAt.
- `AuditEvent`: eventId, aggregateId, actor, eventType, occurredAt, payloadDigest.

## Proposed routes (NOT implemented)
- `GET /api/investigations/:id`: authenticated investigation read.
- `GET /api/reviews/pending`: authenticated reviewer queue.
- `POST /api/reviews/:id/decision`: authenticated, authorized, idempotent human review. Approval means proposal acceptance only, never spending.
- `GET /api/observations?productId=&limit=`: read-only bounded observations.

Request/response JSON, authorization policy, schema migrations and error codes are **undecided**; do not implement routes from these placeholders.

## Critical edge cases before API coding
Duplicate decision submissions; reviewer identity spoofing; stale snapshots; malformed dates/currencies; evidence from another product; synthetic source contamination; request replay; oversized payload; unavailable model; rate limits; schema migration compatibility; immutable history.

## Additive review migration — development-only, NOT applied remotely
File: `cloud/collector/migrations/002_investigation_review.sql` (ADR 002). Three tables:
- `investigations(investigation_id PK, product_id, created_at, evidence_snapshot_hash [64 lowercase hex], proposal_json [valid JSON object], status=PENDING_REVIEW, purchase_authorized=0)`.
- `review_decisions(decision_id PK, investigation_id UNIQUE FK, reviewer_id, decision APPROVE|REJECT, rationale, decided_at, idempotency_key UNIQUE, purchase_authorized=0)`.
- `investigation_audit_events(event_id PK, investigation_id FK, actor_id, event_type INVESTIGATION_CREATED|REVIEW_APPROVED|REVIEW_REJECTED, occurred_at, payload_hash [64 lowercase hex])`.
All three tables reject UPDATE and DELETE. No remote D1 schema application, routes or authenticated write service is included. SQL enforces at most one final decision per investigation; a repeated idempotency key currently fails with a uniqueness error, not a successful replay. The future service must atomically write decision plus audit event, authenticate reviewer and check replay payloads.

## PRODUCT-002C — Provenance des variantes marché

Pour `edge.commercial.snapshot.v1`, le lecteur accepte un champ facultatif
`observations[].variant_evidence` sur un relevé `OK`. Il contient les clés
`language`, `edition`, `condition`, `grading` et `grade`, chacune facultative.
Chaque entrée contient `value` et `source` (URL HTTPS sans identifiants).
Le producteur ne renseigne ces éléments que pour le relevé de prix auquel
ils s'appliquent. La langue de l'URL catalogue et l'ancien booléen ne
permettent pas d'établir la langue du relevé. Une valeur absente ou invalide
reste inconnue. Une note nécessite un gradeur explicite et est incompatible
avec `RAW`. D1 et les routes conservent leurs contrats existants.

Le rapprochement requiert un identifiant exact extension-numéro et un
seul relevé candidat. Il accepte les deux séparateurs historiques des
identifiants EDGE. Un conflit sur une dimension vérifiée des deux côtés
écarte le relevé. Une correspondance candidate conserve sa provenance et
ne donne lieu à aucune attribution de prix ni à aucun conseil d'achat.

## Analyse DeepSeek des variations de prix

Entrée `edge.commercial.events.v1` issue du collecteur existant. Chaque
candidat conserve les deux montants, la fenêtre temporelle, la source
et les deux empreintes. Par défaut, cinq variations maximum par lot,
avec un écart absolu d'au moins 10 %. Sans adaptateur, le résultat est
`DRY_RUN`. Avec adaptateur, la réponse JSON doit contenir exclusivement
`eventId` et `commentary`. Une réponse invalide échoue pour cet événement
et les autres restent traités. Le commentaire est `UNREVIEWED`, sans
effet sur les montants affichés. Aucune route, table D1 ou tâche planifiée
n'est ajoutée par ce lot.

## Catalogue tile prices

`GET /api/catalog/price?lang=fr&id=basep-14` returns `{ price: { low, updatedAt, stale } | null }` for the exact reference. Amounts are EUR indications from Cardmarket via TCGdex. Invalid inputs receive 400, unavailable upstream data receives 503, and missing indications are represented by null. The search and set payloads and D1 schema are unchanged.
