"""Usage metering contract for subscription limits.

Production storage must implement atomic_reserve(). The included in-memory
store is for deterministic tests/local development only; it is not suitable
for multi-worker or serverless production enforcement.
"""
from threading import Lock


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
