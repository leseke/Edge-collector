-- EDGE Outlook/Leboncoin read-only ingestion ledger (development only).
-- This migration is additive; applying to remote D1 requires separate approval.
CREATE TABLE IF NOT EXISTS lbc_alert_messages (
  message_id TEXT PRIMARY KEY NOT NULL,
  received_at TEXT NOT NULL,
  search_name TEXT NOT NULL,
  advertised_count INTEGER NOT NULL CHECK (advertised_count >= 0),
  extracted_count INTEGER NOT NULL CHECK (extracted_count >= 0),
  truncated_email INTEGER NOT NULL CHECK (truncated_email IN (0,1)),
  ingested_at TEXT NOT NULL,
  CHECK (extracted_count <= advertised_count OR advertised_count = 0)
);
CREATE INDEX IF NOT EXISTS lbc_alert_messages_received ON lbc_alert_messages(received_at DESC);
CREATE TRIGGER IF NOT EXISTS lbc_alert_messages_no_update BEFORE UPDATE ON lbc_alert_messages
BEGIN SELECT RAISE(ABORT,'immutable_lbc_message'); END;
CREATE TRIGGER IF NOT EXISTS lbc_alert_messages_no_delete BEFORE DELETE ON lbc_alert_messages
BEGIN SELECT RAISE(ABORT,'immutable_lbc_message'); END;

-- Listing excerpts are observations, not proof an ad is currently live.
-- Repeated listing IDs from distinct emails remain separate historical evidence.
CREATE TABLE IF NOT EXISTS lbc_listing_observations (
  message_id TEXT NOT NULL REFERENCES lbc_alert_messages(message_id),
  listing_id TEXT NOT NULL CHECK (listing_id GLOB 'leboncoin:[0-9]*'),
  observed_at TEXT NOT NULL,
  source_url TEXT NOT NULL,
  title TEXT,
  price_cents INTEGER CHECK (price_cents IS NULL OR price_cents >= 0),
  currency TEXT CHECK (currency IS NULL OR currency = 'EUR'),
  location TEXT,
  category_hint TEXT NOT NULL,
  price_kind TEXT NOT NULL DEFAULT 'LISTING' CHECK (price_kind = 'LISTING'),
  availability TEXT NOT NULL DEFAULT 'UNVERIFIED' CHECK (availability = 'UNVERIFIED'),
  evidence TEXT NOT NULL DEFAULT 'EMAIL_EXCERPT' CHECK (evidence = 'EMAIL_EXCERPT'),
  PRIMARY KEY (message_id,listing_id)
);
CREATE INDEX IF NOT EXISTS lbc_listing_observations_recent ON lbc_listing_observations(observed_at DESC,listing_id);
CREATE INDEX IF NOT EXISTS lbc_listing_observations_history ON lbc_listing_observations(listing_id,observed_at DESC);
CREATE TRIGGER IF NOT EXISTS lbc_listing_observations_no_update BEFORE UPDATE ON lbc_listing_observations
BEGIN SELECT RAISE(ABORT,'immutable_lbc_listing'); END;
CREATE TRIGGER IF NOT EXISTS lbc_listing_observations_no_delete BEFORE DELETE ON lbc_listing_observations
BEGIN SELECT RAISE(ABORT,'immutable_lbc_listing'); END;
