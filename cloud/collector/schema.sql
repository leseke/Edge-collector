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
