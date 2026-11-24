CREATE TABLE IF NOT EXISTS commercial_research_observations (
 source_url TEXT NOT NULL,
 observed_at TEXT NOT NULL,
 merchant TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('READ','FAILED')),
 evidence_json TEXT NOT NULL CHECK(json_valid(evidence_json)),
 payload_sha256 TEXT,
 PRIMARY KEY(source_url,observed_at)
) WITHOUT ROWID;
CREATE TRIGGER IF NOT EXISTS commercial_research_no_update BEFORE UPDATE ON commercial_research_observations BEGIN SELECT RAISE(ABORT,'immutable_commercial_research'); END;
CREATE TRIGGER IF NOT EXISTS commercial_research_no_delete BEFORE DELETE ON commercial_research_observations BEGIN SELECT RAISE(ABORT,'immutable_commercial_research'); END;
