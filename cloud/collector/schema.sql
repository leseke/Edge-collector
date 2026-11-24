-- EDGE cloud collector v1 — immutable observations; never rewrite history.
CREATE TABLE IF NOT EXISTS collection_runs (
  run_id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL CHECK (status IN ('RUNNING','OK','PARTIAL','FAILED','EMPTY')),
  attempted INTEGER NOT NULL DEFAULT 0,
  succeeded INTEGER NOT NULL DEFAULT 0,
  failed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS observations (
  observation_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES collection_runs(run_id),
  product_id TEXT NOT NULL,
  source TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  price_cents INTEGER,
  currency TEXT,
  availability TEXT NOT NULL DEFAULT 'UNKNOWN',
  price_kind TEXT NOT NULL CHECK (price_kind IN ('LISTING','AGGREGATE','COMPLETED_SALE')),
  source_url TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  source_updated_at TEXT,
  CHECK (price_cents IS NULL OR price_cents >= 0)
);
CREATE INDEX IF NOT EXISTS observations_product_time ON observations(product_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS observations_run ON observations(run_id);

-- Protect historical observations from accidental updates or deletion.
CREATE TRIGGER IF NOT EXISTS observations_no_update
BEFORE UPDATE ON observations BEGIN
  SELECT RAISE(ABORT, 'immutable_observation');
END;
CREATE TRIGGER IF NOT EXISTS observations_no_delete
BEFORE DELETE ON observations BEGIN
  SELECT RAISE(ABORT, 'immutable_observation');
END;

-- Every failed source attempt is retained, including runs with no successful prices.
CREATE TABLE IF NOT EXISTS collection_errors (
  error_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES collection_runs(run_id),
  product_id TEXT NOT NULL,
  source_url TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  reason_code TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS collection_errors_run ON collection_errors(run_id);
CREATE TRIGGER IF NOT EXISTS collection_errors_no_update
BEFORE UPDATE ON collection_errors BEGIN SELECT RAISE(ABORT, 'immutable_error'); END;
CREATE TRIGGER IF NOT EXISTS collection_errors_no_delete
BEFORE DELETE ON collection_errors BEGIN SELECT RAISE(ABORT, 'immutable_error'); END;

-- At most one result of each kind per target per run.
-- Prevents accidental duplicate writes during retries without deduplicating
-- genuinely new observations from separate collection runs.
CREATE UNIQUE INDEX IF NOT EXISTS observations_run_product_unique
ON observations(run_id, product_id);
CREATE UNIQUE INDEX IF NOT EXISTS collection_errors_run_product_unique
ON collection_errors(run_id, product_id);

CREATE TABLE IF NOT EXISTS paid_sale_scans (
  scan_day TEXT PRIMARY KEY,
  status TEXT NOT NULL CHECK (status IN ('RUNNING','OK','EMPTY','PARTIAL','FAILED')),
  checked INTEGER NOT NULL DEFAULT 0,
  verified INTEGER NOT NULL DEFAULT 0,
  inserted INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS paid_market_sales (
  lot_id TEXT PRIMARY KEY,
  variant_key TEXT NOT NULL,
  sold_day TEXT NOT NULL,
  price_cents INTEGER NOT NULL CHECK (price_cents > 0),
  source_url TEXT NOT NULL,
  collected_at TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS paid_market_sales_variant_day ON paid_market_sales(variant_key,sold_day DESC);
CREATE TRIGGER IF NOT EXISTS paid_market_sales_no_update
BEFORE UPDATE ON paid_market_sales BEGIN SELECT RAISE(ABORT, 'immutable_paid_sale'); END;
CREATE TRIGGER IF NOT EXISTS paid_market_sales_no_delete
BEFORE DELETE ON paid_market_sales BEGIN SELECT RAISE(ABORT, 'immutable_paid_sale'); END;

CREATE TABLE IF NOT EXISTS market_discovery_leads (
  source_url TEXT PRIMARY KEY,
  category TEXT NOT NULL CHECK (category IN ('CARTE','BOOSTER','COFFRET','SORTIE')),
  kind TEXT NOT NULL CHECK (kind IN ('LOT','ANNONCE','PUBLICATION')),
  first_seen_day TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS market_discovery_leads_day ON market_discovery_leads(first_seen_day DESC);

CREATE TABLE IF NOT EXISTS gcc_lot_queue (
  lot_id TEXT PRIMARY KEY,
  first_seen_day TEXT NOT NULL,
  next_check_day TEXT NOT NULL,
  paid_day TEXT
);
CREATE INDEX IF NOT EXISTS gcc_lot_queue_due ON gcc_lot_queue(paid_day,next_check_day,first_seen_day);

CREATE TABLE IF NOT EXISTS gcc_listing_cursor (
  category TEXT PRIMARY KEY CHECK (category IN ('AUCTIONS','FIXED_PRICE')),
  next_page INTEGER NOT NULL CHECK (next_page >= 1)
);

CREATE TABLE IF NOT EXISTS gcc_public_index (
  lot_id TEXT PRIMARY KEY,
  source_modified_day TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gcc_coverage (
  kind TEXT PRIMARY KEY CHECK(kind IN ('closed','fixed','auction')),
  cycle INTEGER NOT NULL DEFAULT 1,
  page INTEGER NOT NULL DEFAULT 0,
  cursor TEXT,
  announced INTEGER,
  observed INTEGER NOT NULL DEFAULT 0,
  checked_at TEXT,
  last_complete TEXT,
  finished INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS gcc_coverage_ids (
  kind TEXT NOT NULL,
  lot_id TEXT NOT NULL,
  PRIMARY KEY(kind,lot_id)
) WITHOUT ROWID;

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
