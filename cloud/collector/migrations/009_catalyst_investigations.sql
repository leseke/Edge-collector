-- A dossier is an immutable observation of a publisher article, not a verified investment thesis.
CREATE TABLE IF NOT EXISTS catalyst_investigations (
 source_url TEXT NOT NULL REFERENCES catalyst_discoveries(source_url),
 observed_at TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('READ','FAILED')),
 headline TEXT,
 description TEXT,
 published_at TEXT,
 payload_sha256 TEXT,
 error_code TEXT,
 PRIMARY KEY(source_url,observed_at)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS catalyst_investigation_time ON catalyst_investigations(source_url,observed_at DESC);
CREATE TRIGGER IF NOT EXISTS catalyst_investigation_no_update BEFORE UPDATE ON catalyst_investigations BEGIN SELECT RAISE(ABORT,'immutable_investigation'); END;
CREATE TRIGGER IF NOT EXISTS catalyst_investigation_no_delete BEFORE DELETE ON catalyst_investigations BEGIN SELECT RAISE(ABORT,'immutable_investigation'); END;
