CREATE TABLE IF NOT EXISTS catalyst_discoveries (
 source_url TEXT PRIMARY KEY, publisher TEXT NOT NULL, title TEXT NOT NULL,
 first_seen_at TEXT NOT NULL, payload_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS catalyst_scan_runs (
 run_id TEXT PRIMARY KEY, observed_at TEXT NOT NULL, publisher TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('OK','EMPTY','FAILED')), discovered INTEGER NOT NULL
);
CREATE TRIGGER IF NOT EXISTS catalyst_discoveries_no_update BEFORE UPDATE ON catalyst_discoveries BEGIN SELECT RAISE(ABORT,'immutable_catalyst'); END;
CREATE TRIGGER IF NOT EXISTS catalyst_discoveries_no_delete BEFORE DELETE ON catalyst_discoveries BEGIN SELECT RAISE(ABORT,'immutable_catalyst'); END;
