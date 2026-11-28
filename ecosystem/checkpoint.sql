-- Apply after memory.sql in a reviewed non-production database.
CREATE TABLE IF NOT EXISTS ecosystem_checkpoint (
 id TEXT PRIMARY KEY NOT NULL,
 version INTEGER NOT NULL CHECK(version>=0),
 state_json TEXT NOT NULL CHECK(json_valid(state_json)),
 updated_at INTEGER NOT NULL CHECK(updated_at>=0)
);
