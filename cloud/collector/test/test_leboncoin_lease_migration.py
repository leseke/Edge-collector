"""SQLite compatibility checks for the Outlook concurrency lease."""
import pathlib
import sqlite3
import unittest

MIGRATION = pathlib.Path(__file__).resolve().parents[1] / "migrations" / "006_outlook_run_lease.sql"

class OutlookLeaseMigrationTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript(MIGRATION.read_text(encoding="utf-8"))
    def tearDown(self):
        self.db.close()
    def attempt(self, lease_id, acquired_at_ms, ttl_ms=120000):
        return self.db.execute("""INSERT INTO lbc_sync_lease
          (owner_key,lease_id,expires_at_ms,acquired_at_ms) VALUES (?,?,?,?)
          ON CONFLICT(owner_key) DO UPDATE SET
          lease_id=excluded.lease_id,expires_at_ms=excluded.expires_at_ms,
          acquired_at_ms=excluded.acquired_at_ms
          WHERE lbc_sync_lease.expires_at_ms <= excluded.acquired_at_ms""",
          ("a"*64, lease_id, acquired_at_ms+ttl_ms, acquired_at_ms)).rowcount
    def test_concurrent_runs_do_not_overlap(self):
        self.assertEqual(self.attempt("A"*32,1000),1)
        self.assertEqual(self.attempt("B"*32,1001),0)
        self.assertEqual(self.db.execute("SELECT lease_id FROM lbc_sync_lease").fetchone()[0],"A"*32)
    def test_reclaim_after_expiry_and_stale_release(self):
        self.assertEqual(self.attempt("A"*32,1000),1)
        self.assertEqual(self.attempt("B"*32,121000),1)
        stale=self.db.execute("DELETE FROM lbc_sync_lease WHERE owner_key=? AND lease_id=?",("a"*64,"A"*32))
        self.assertEqual(stale.rowcount,0)
        self.assertEqual(self.db.execute("SELECT lease_id FROM lbc_sync_lease").fetchone()[0],"B"*32)
    def test_invalid_owner_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO lbc_sync_lease VALUES (?,?,?,?)",("bad","A"*32,10000,1000))

if __name__=="__main__":
    unittest.main()
