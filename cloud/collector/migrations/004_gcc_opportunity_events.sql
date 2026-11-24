-- Immutable research decisions, never purchase authorizations.
CREATE TABLE IF NOT EXISTS gcc_opportunity_events (
  lot_id TEXT NOT NULL,
  cycle INTEGER NOT NULL,
  page INTEGER NOT NULL,
  observed_at TEXT NOT NULL,
  variant_key TEXT,
  title TEXT NOT NULL,
  asking_cents INTEGER NOT NULL CHECK(asking_cents > 0),
  median_cents INTEGER,
  comparable_count INTEGER NOT NULL CHECK(comparable_count >= 0),
  headroom_cents INTEGER,
  status TEXT NOT NULL CHECK(status IN ('INVESTIGATE','THIN_MARGIN','NO_DISCOUNT','INSUFFICIENT')),
  evidence_json TEXT NOT NULL CHECK(json_valid(evidence_json)),
  resale_fee_percent INTEGER NOT NULL,
  PRIMARY KEY(lot_id,cycle,page)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS gcc_opportunity_events_time ON gcc_opportunity_events(observed_at DESC);
CREATE TRIGGER IF NOT EXISTS gcc_opportunity_events_no_update BEFORE UPDATE ON gcc_opportunity_events BEGIN SELECT RAISE(ABORT,'immutable_opportunity'); END;
CREATE TRIGGER IF NOT EXISTS gcc_opportunity_events_no_delete BEFORE DELETE ON gcc_opportunity_events BEGIN SELECT RAISE(ABORT,'immutable_opportunity'); END;
