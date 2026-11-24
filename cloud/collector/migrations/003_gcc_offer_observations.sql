-- Append-only observations of open GCC offers, distinct from paid sales.
CREATE TABLE IF NOT EXISTS gcc_offer_observations (
  kind TEXT NOT NULL CHECK(kind IN ('fixed','auction')),
  lot_id TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  cycle INTEGER NOT NULL CHECK(cycle >= 1),
  page INTEGER NOT NULL CHECK(page >= 1),
  variant_key TEXT,
  title TEXT NOT NULL,
  price_cents INTEGER CHECK(price_cents IS NULL OR price_cents > 0),
  ends_at TEXT,
  source_url TEXT NOT NULL,
  PRIMARY KEY(kind,lot_id,cycle,page)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS gcc_offer_observations_lot_time ON gcc_offer_observations(lot_id,observed_at DESC);
CREATE INDEX IF NOT EXISTS gcc_offer_observations_variant_time ON gcc_offer_observations(variant_key,observed_at DESC);
CREATE TRIGGER IF NOT EXISTS gcc_offer_observations_no_update
BEFORE UPDATE ON gcc_offer_observations BEGIN SELECT RAISE(ABORT,'immutable_offer_observation'); END;
CREATE TRIGGER IF NOT EXISTS gcc_offer_observations_no_delete
BEFORE DELETE ON gcc_offer_observations BEGIN SELECT RAISE(ABORT,'immutable_offer_observation'); END;
