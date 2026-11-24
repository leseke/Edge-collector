-- Lifecycle observations do not imply a sale.
CREATE TABLE IF NOT EXISTS gcc_lifecycle_events (
 lot_id TEXT NOT NULL,
 cycle INTEGER NOT NULL,
 observed_at TEXT NOT NULL,
 event TEXT NOT NULL CHECK(event IN ('FIRST_SEEN','NOT_SEEN','REAPPEARED')),
 PRIMARY KEY(lot_id,cycle,event)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS gcc_lifecycle_recent ON gcc_lifecycle_events(observed_at DESC);
CREATE TRIGGER IF NOT EXISTS gcc_lifecycle_no_update BEFORE UPDATE ON gcc_lifecycle_events BEGIN SELECT RAISE(ABORT,'immutable_lifecycle'); END;
CREATE TRIGGER IF NOT EXISTS gcc_lifecycle_no_delete BEFORE DELETE ON gcc_lifecycle_events BEGIN SELECT RAISE(ABORT,'immutable_lifecycle'); END;
CREATE INDEX IF NOT EXISTS gcc_offer_cycle ON gcc_offer_observations(kind,cycle,lot_id);
