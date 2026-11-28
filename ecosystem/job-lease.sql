CREATE TABLE IF NOT EXISTS ecosystem_job_lease (
 scope TEXT NOT NULL,
 job_id TEXT NOT NULL,
 token TEXT NOT NULL,
 expires_at INTEGER NOT NULL CHECK(expires_at>=0),
 completed_at INTEGER,
 PRIMARY KEY(scope,job_id)
);
