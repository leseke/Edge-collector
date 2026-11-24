"""Usage metering contract for subscription limits.

Production storage must implement atomic_reserve(). The included in-memory
store is for deterministic tests/local development only; it is not suitable
for multi-worker or serverless production enforcement.
"""
from threading import Lock
import sqlite3


class UsageLimitExceeded(RuntimeError):
    pass


class InMemoryUsageStore:
    """Test-only store; do not use as a production billing ledger."""
    test_only = True

    def __init__(self):
        self._lock = Lock()
        self._reservations = {}

    def atomic_reserve(self, key, limit):
        with self._lock:
            if key in self._reservations:
                return self._reservations[key]
            count = sum(1 for item in self._reservations.values()
                        if item["bucket"] == key.rsplit(":", 1)[0])
            if count >= limit:
                raise UsageLimitExceeded("quota EDGE atteinte")
            record = {"bucket": key.rsplit(":", 1)[0], "key": key}
            self._reservations[key] = record
            return record


def reserve_usage(store, user_key, period, metric, limit, idempotency_key):
    """Reserve one unit atomically; caller supplies a persistent store in prod."""
    for value, label in ((user_key, "user_key"), (period, "period"),
                         (metric, "metric"), (idempotency_key, "idempotency_key")):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(label + " requis")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit doit etre un entier positif")
    reserve = getattr(store, "atomic_reserve", None)
    if not callable(reserve):
        raise TypeError("store doit implementer atomic_reserve")
    key = f"{user_key}:{period}:{metric}:{idempotency_key}"
    bucket = f"{user_key}:{period}:{metric}"
    return reserve(key, limit)


class SQLiteUsageStore:
    """Persistent single-node store using SQLite transactions.

    Use only on a durable filesystem with one application host. Serverless or
    multi-instance deployments must provide a shared transactional store
    (for example PostgreSQL) implementing the same atomic_reserve contract.
    """
    test_only = False

    def __init__(self, database_path, timeout=10):
        if not isinstance(database_path, str) or not database_path.strip():
            raise ValueError("database_path requis")
        self.database_path = database_path
        self.timeout = timeout
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS edge_usage_reservations (
                    reservation_key TEXT PRIMARY KEY,
                    bucket TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_edge_usage_bucket "
                       "ON edge_usage_reservations(bucket)")

    def _connect(self):
        db = sqlite3.connect(self.database_path, timeout=self.timeout,
                             isolation_level=None)
        db.execute("PRAGMA busy_timeout = 10000")
        return db

    def atomic_reserve(self, key, limit):
        if not isinstance(key, str) or not key:
            raise ValueError("reservation key requis")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit doit etre un entier positif")
        bucket = key.rsplit(":", 1)[0]
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT reservation_key, bucket FROM edge_usage_reservations "
                "WHERE reservation_key = ?", (key,)).fetchone()
            if existing:
                db.execute("COMMIT")
                return {"key": existing[0], "bucket": existing[1]}
            count = db.execute(
                "SELECT COUNT(*) FROM edge_usage_reservations WHERE bucket = ?",
                (bucket,)).fetchone()[0]
            if count >= limit:
                db.execute("ROLLBACK")
                raise UsageLimitExceeded("quota EDGE atteinte")
            db.execute("INSERT INTO edge_usage_reservations(reservation_key, bucket) VALUES (?, ?)",
                       (key, bucket))
            db.execute("COMMIT")
            return {"key": key, "bucket": bucket}
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()
