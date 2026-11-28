CREATE TABLE IF NOT EXISTS ecosystem_external_operation (
 scope TEXT NOT NULL,
 operation_id TEXT NOT NULL,
 fingerprint TEXT NOT NULL,
 token TEXT NOT NULL,
 started_at INTEGER NOT NULL CHECK(started_at>=0),
 completed_at INTEGER,
 result_json TEXT CHECK(result_json IS NULL OR json_valid(result_json)),
 PRIMARY KEY(scope,operation_id),
 CHECK((completed_at IS NULL AND result_json IS NULL) OR (completed_at>=started_at AND result_json IS NOT NULL))
);
CREATE TRIGGER IF NOT EXISTS ecosystem_external_no_delete BEFORE DELETE ON ecosystem_external_operation
BEGIN SELECT RAISE(ABORT,'external operation history is immutable'); END;
CREATE TRIGGER IF NOT EXISTS ecosystem_external_update_guard BEFORE UPDATE ON ecosystem_external_operation
WHEN OLD.completed_at IS NOT NULL OR NEW.scope<>OLD.scope OR NEW.operation_id<>OLD.operation_id OR NEW.fingerprint<>OLD.fingerprint OR NEW.token<>OLD.token OR NEW.started_at<>OLD.started_at OR NEW.completed_at IS NULL
BEGIN SELECT RAISE(ABORT,'invalid external operation transition'); END;
