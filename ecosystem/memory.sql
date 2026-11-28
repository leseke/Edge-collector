-- Proposed SQLite/D1 migration. Apply only after reviewing existing schema.
CREATE TABLE IF NOT EXISTS ecosystem_memory (
 id TEXT PRIMARY KEY NOT NULL,
 subject TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('observation','verification','hypothesis','outcome','decision')),
 recorded_at INTEGER NOT NULL,
 occurred_at INTEGER NOT NULL CHECK(occurred_at>=0 AND occurred_at<=recorded_at),
 statement TEXT NOT NULL,
 source_url TEXT,
 hypothesis_id TEXT REFERENCES ecosystem_memory(id),
 outcome TEXT CHECK(outcome IN ('supported','contradicted','inconclusive')),
 CHECK(kind!='observation' OR source_url IS NOT NULL),
 CHECK((kind='outcome' AND hypothesis_id IS NOT NULL AND outcome IS NOT NULL) OR (kind!='outcome' AND hypothesis_id IS NULL AND outcome IS NULL))
);
CREATE INDEX IF NOT EXISTS ecosystem_memory_timeline ON ecosystem_memory(subject,recorded_at DESC,id);
CREATE TABLE IF NOT EXISTS ecosystem_memory_evidence (
 entry_id TEXT NOT NULL REFERENCES ecosystem_memory(id),
 evidence_id TEXT NOT NULL REFERENCES ecosystem_memory(id),
 PRIMARY KEY(entry_id,evidence_id),
 CHECK(entry_id!=evidence_id)
);
CREATE TRIGGER IF NOT EXISTS ecosystem_memory_no_update BEFORE UPDATE ON ecosystem_memory BEGIN SELECT RAISE(ABORT,'immutable memory'); END;
CREATE TRIGGER IF NOT EXISTS ecosystem_memory_no_delete BEFORE DELETE ON ecosystem_memory BEGIN SELECT RAISE(ABORT,'immutable memory'); END;
CREATE TRIGGER IF NOT EXISTS ecosystem_memory_evidence_no_update BEFORE UPDATE ON ecosystem_memory_evidence BEGIN SELECT RAISE(ABORT,'immutable evidence link'); END;
CREATE TRIGGER IF NOT EXISTS ecosystem_memory_evidence_no_delete BEFORE DELETE ON ecosystem_memory_evidence BEGIN SELECT RAISE(ABORT,'immutable evidence link'); END;
