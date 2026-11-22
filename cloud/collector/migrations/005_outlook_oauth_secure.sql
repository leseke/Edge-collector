-- Proposed development-only storage for confidential Microsoft OAuth.
-- Never apply remotely before a verified server-side session and consent flow.
CREATE TABLE IF NOT EXISTS lbc_oauth_pending (
  state_hash TEXT PRIMARY KEY NOT NULL CHECK(length(state_hash) BETWEEN 40 AND 64),
  ciphertext_b64 TEXT NOT NULL,
  nonce_b64 TEXT NOT NULL,
  expires_at INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS lbc_oauth_pending_expiry ON lbc_oauth_pending(expires_at);

CREATE TABLE IF NOT EXISTS lbc_oauth_credentials (
  mailbox_key TEXT PRIMARY KEY NOT NULL CHECK(length(mailbox_key) BETWEEN 16 AND 128),
  ciphertext_b64 TEXT NOT NULL,
  nonce_b64 TEXT NOT NULL,
  generation INTEGER NOT NULL DEFAULT 1 CHECK(generation >= 1),
  modified_at TEXT NOT NULL
);
-- Pending requests are consumed atomically. Credentials are mutable for rotation;
-- individual listing/message observations remain append-only.
