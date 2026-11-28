CREATE TABLE IF NOT EXISTS ecosystem_dispatch_lock (
 scope TEXT PRIMARY KEY NOT NULL,
 token TEXT NOT NULL,
 expires_at INTEGER NOT NULL CHECK(expires_at>=0)
);
