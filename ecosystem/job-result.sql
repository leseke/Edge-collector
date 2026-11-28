CREATE TABLE IF NOT EXISTS ecosystem_job_result (
 scope TEXT NOT NULL,
 job_id TEXT NOT NULL,
 token TEXT NOT NULL,
 completed_at INTEGER NOT NULL CHECK(completed_at>=0),
 result_json TEXT NOT NULL CHECK(json_valid(result_json)),
 PRIMARY KEY(scope,job_id),
 FOREIGN KEY(scope,job_id) REFERENCES ecosystem_job_lease(scope,job_id)
);
CREATE TRIGGER IF NOT EXISTS ecosystem_result_fence BEFORE INSERT ON ecosystem_job_result
WHEN NOT EXISTS (SELECT 1 FROM ecosystem_job_lease WHERE scope=NEW.scope AND job_id=NEW.job_id AND token=NEW.token AND completed_at IS NULL AND expires_at>NEW.completed_at)
BEGIN SELECT RAISE(ABORT,'invalid result owner'); END;
CREATE TRIGGER IF NOT EXISTS ecosystem_result_complete AFTER INSERT ON ecosystem_job_result
BEGIN UPDATE ecosystem_job_lease SET completed_at=NEW.completed_at WHERE scope=NEW.scope AND job_id=NEW.job_id; END;
CREATE TRIGGER IF NOT EXISTS ecosystem_result_immutable BEFORE UPDATE ON ecosystem_job_result BEGIN SELECT RAISE(ABORT,'immutable result'); END;
CREATE TRIGGER IF NOT EXISTS ecosystem_result_no_delete BEFORE DELETE ON ecosystem_job_result BEGIN SELECT RAISE(ABORT,'immutable result'); END;
