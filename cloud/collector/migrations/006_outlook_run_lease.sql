-- Additive single-operator Outlook ingestion lease, not applied to production.
-- One active run per pseudonymous EDGE owner; stale leases may be reclaimed.
CREATE TABLE IF NOT EXISTS lbc_sync_lease (
  owner_key TEXT PRIMARY KEY NOT NULL CHECK(length(owner_key)=64),
  lease_id TEXT NOT NULL CHECK(length(lease_id) BETWEEN 32 AND 80),
  expires_at_ms INTEGER NOT NULL,
  acquired_at_ms INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS lbc_sync_lease_expiry ON lbc_sync_lease(expires_at_ms);
