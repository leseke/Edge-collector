-- Pending activation: encrypted opaque Graph delta cursor only.
-- No OAuth tokens or mailbox text are stored by this migration.
CREATE TABLE IF NOT EXISTS lbc_graph_delta_cursor (
  mailbox_key TEXT PRIMARY KEY CHECK(length(mailbox_key) BETWEEN 16 AND 128),
  nonce_b64 TEXT NOT NULL,
  ciphertext_b64 TEXT NOT NULL,
  generation INTEGER NOT NULL DEFAULT 1 CHECK(generation >= 1),
  modified_at TEXT NOT NULL
);
-- Mutable operational checkpoint. Historical listing/message tables remain immutable.
