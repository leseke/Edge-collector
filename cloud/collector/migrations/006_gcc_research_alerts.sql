-- Internal alert inbox: append-only, no external delivery or purchase permission.
CREATE TABLE IF NOT EXISTS gcc_research_alerts (
 lot_id TEXT NOT NULL,
 cycle INTEGER NOT NULL,
 page INTEGER NOT NULL,
 observed_at TEXT NOT NULL,
 reason TEXT NOT NULL CHECK(reason IN ('NEW_OPPORTUNITY','STATUS_IMPROVED','PRICE_DROP','REAPPEARED')),
 asking_cents INTEGER NOT NULL,
 previous_cents INTEGER,
 status TEXT NOT NULL,
 PRIMARY KEY(lot_id,cycle,page)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS gcc_research_alerts_time ON gcc_research_alerts(observed_at DESC);
CREATE TRIGGER IF NOT EXISTS gcc_alerts_no_update BEFORE UPDATE ON gcc_research_alerts BEGIN SELECT RAISE(ABORT,'immutable_alert'); END;
CREATE TRIGGER IF NOT EXISTS gcc_alerts_no_delete BEFORE DELETE ON gcc_research_alerts BEGIN SELECT RAISE(ABORT,'immutable_alert'); END;
