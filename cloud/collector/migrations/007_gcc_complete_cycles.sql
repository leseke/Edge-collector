-- Immutable count-matched traversal checkpoints, not claims of a market-wide census.
CREATE TABLE IF NOT EXISTS gcc_complete_cycles (
 kind TEXT NOT NULL CHECK(kind IN ('fixed','auction')),
 cycle INTEGER NOT NULL,
 completed_at TEXT NOT NULL,
 announced INTEGER NOT NULL CHECK(announced>=0),
 PRIMARY KEY(kind,cycle)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS gcc_complete_cycles_time ON gcc_complete_cycles(kind,completed_at DESC);
CREATE TRIGGER IF NOT EXISTS gcc_complete_cycles_no_update BEFORE UPDATE ON gcc_complete_cycles BEGIN SELECT RAISE(ABORT,'immutable_cycle'); END;
CREATE TRIGGER IF NOT EXISTS gcc_complete_cycles_no_delete BEFORE DELETE ON gcc_complete_cycles BEGIN SELECT RAISE(ABORT,'immutable_cycle'); END;
