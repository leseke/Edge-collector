-- EDGE review persistence v1: additive, never modifies collector observations.
-- Apply only after an explicitly approved D1 migration; not deployed by this commit.
CREATE TABLE IF NOT EXISTS investigations (
  investigation_id TEXT PRIMARY KEY NOT NULL CHECK (length(investigation_id) BETWEEN 1 AND 120),
  product_id TEXT NOT NULL CHECK (length(product_id) BETWEEN 1 AND 120),
  created_at TEXT NOT NULL CHECK (length(created_at) >= 20),
  evidence_snapshot_hash TEXT NOT NULL CHECK (length(evidence_snapshot_hash) = 64 AND evidence_snapshot_hash NOT GLOB '*[^0-9a-f]*'),
  proposal_json TEXT NOT NULL CHECK (json_valid(proposal_json) AND json_type(proposal_json) = 'object'),
  status TEXT NOT NULL DEFAULT 'PENDING_REVIEW' CHECK (status = 'PENDING_REVIEW'),
  purchase_authorized INTEGER NOT NULL DEFAULT 0 CHECK (purchase_authorized = 0)
);
CREATE INDEX IF NOT EXISTS investigations_product_created ON investigations(product_id,created_at DESC);
CREATE TRIGGER IF NOT EXISTS investigations_no_update BEFORE UPDATE ON investigations
BEGIN SELECT RAISE(ABORT,'immutable_investigation'); END;
CREATE TRIGGER IF NOT EXISTS investigations_no_delete BEFORE DELETE ON investigations
BEGIN SELECT RAISE(ABORT,'immutable_investigation'); END;

CREATE TABLE IF NOT EXISTS review_decisions (
  decision_id TEXT PRIMARY KEY NOT NULL CHECK (length(decision_id) BETWEEN 1 AND 120),
  investigation_id TEXT NOT NULL UNIQUE REFERENCES investigations(investigation_id),
  reviewer_id TEXT NOT NULL CHECK (length(trim(reviewer_id)) BETWEEN 1 AND 120),
  decision TEXT NOT NULL CHECK (decision IN ('APPROVE','REJECT')),
  rationale TEXT NOT NULL CHECK (length(trim(rationale)) BETWEEN 1 AND 2000),
  decided_at TEXT NOT NULL CHECK (length(decided_at) >= 20),
  idempotency_key TEXT NOT NULL UNIQUE CHECK (length(idempotency_key) BETWEEN 1 AND 120),
  purchase_authorized INTEGER NOT NULL DEFAULT 0 CHECK (purchase_authorized = 0)
);
CREATE TRIGGER IF NOT EXISTS review_decisions_no_update BEFORE UPDATE ON review_decisions
BEGIN SELECT RAISE(ABORT,'immutable_review_decision'); END;
CREATE TRIGGER IF NOT EXISTS review_decisions_no_delete BEFORE DELETE ON review_decisions
BEGIN SELECT RAISE(ABORT,'immutable_review_decision'); END;

CREATE TABLE IF NOT EXISTS investigation_audit_events (
  event_id TEXT PRIMARY KEY NOT NULL CHECK (length(event_id) BETWEEN 1 AND 120),
  investigation_id TEXT NOT NULL REFERENCES investigations(investigation_id),
  actor_id TEXT NOT NULL CHECK (length(trim(actor_id)) BETWEEN 1 AND 120),
  event_type TEXT NOT NULL CHECK (event_type IN ('INVESTIGATION_CREATED','REVIEW_APPROVED','REVIEW_REJECTED')),
  occurred_at TEXT NOT NULL CHECK (length(occurred_at) >= 20),
  payload_hash TEXT NOT NULL CHECK (length(payload_hash) = 64 AND payload_hash NOT GLOB '*[^0-9a-f]*')
);
CREATE INDEX IF NOT EXISTS investigation_audit_by_investigation ON investigation_audit_events(investigation_id,occurred_at);
CREATE TRIGGER IF NOT EXISTS investigation_audit_no_update BEFORE UPDATE ON investigation_audit_events
BEGIN SELECT RAISE(ABORT,'immutable_audit_event'); END;
CREATE TRIGGER IF NOT EXISTS investigation_audit_no_delete BEFORE DELETE ON investigation_audit_events
BEGIN SELECT RAISE(ABORT,'immutable_audit_event'); END;
