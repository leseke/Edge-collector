CREATE TABLE IF NOT EXISTS ecosystem_recovery_state (
 scope TEXT PRIMARY KEY NOT NULL,
 version INTEGER NOT NULL CHECK(version>=0),
 state_json TEXT NOT NULL CHECK(json_valid(state_json))
);
