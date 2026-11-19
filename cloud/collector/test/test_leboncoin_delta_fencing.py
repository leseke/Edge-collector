"""SQLite compatibility and atomic fencing checks for Outlook Delta checkpoints."""
import pathlib
import sqlite3
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
class DeltaFencingMigrationTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.executescript((ROOT/"migrations"/"004_outlook_delta_cursor.sql").read_text())
        self.db.executescript((ROOT/"migrations"/"006_outlook_run_lease.sql").read_text())
        self.owner="a"*64
        self.lease="123e4567-e89b-12d3-a456-426614174000"
        self.now=1000000
    def tearDown(self):
        self.db.close()
    def acquire(self,lease=None,expiry=None):
        self.db.execute("""INSERT INTO lbc_sync_lease(owner_key,lease_id,expires_at_ms,acquired_at_ms)
        VALUES (?,?,?,?) ON CONFLICT(owner_key) DO UPDATE SET
        lease_id=excluded.lease_id,expires_at_ms=excluded.expires_at_ms,
        acquired_at_ms=excluded.acquired_at_ms""",
        (self.owner,lease or self.lease,expiry or 2000000,self.now))
    def insert_cursor(self):
        return self.db.execute("""INSERT OR IGNORE INTO lbc_graph_delta_cursor
        (mailbox_key,nonce_b64,ciphertext_b64,generation,modified_at)
        SELECT ?,?,?,1,? WHERE EXISTS (SELECT 1 FROM lbc_sync_lease
        WHERE owner_key = ? AND lease_id = ? AND expires_at_ms > ?)""",
        (self.owner,"iv","encrypted", "2026-11-19T00:00:00Z",self.owner,self.lease,self.now)).rowcount
    def update_cursor(self):
        return self.db.execute("""UPDATE lbc_graph_delta_cursor SET nonce_b64=?,ciphertext_b64=?,
        generation=generation+1,modified_at=? WHERE mailbox_key=? AND generation=? AND EXISTS
        (SELECT 1 FROM lbc_sync_lease WHERE owner_key = ? AND lease_id = ? AND expires_at_ms > ?)""",
        ("iv2","encrypted2","2026-11-19T00:00:01Z",self.owner,1,self.owner,self.lease,self.now)).rowcount
    def test_no_lease_no_checkpoint(self):
        self.assertEqual(self.insert_cursor(),0)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM lbc_graph_delta_cursor").fetchone()[0],0)
    def test_replaced_lease_blocks_cursor_update(self):
        self.acquire()
        self.assertEqual(self.insert_cursor(),1)
        self.acquire("b"*36)
        self.assertEqual(self.update_cursor(),0)
        self.assertEqual(self.db.execute("SELECT generation FROM lbc_graph_delta_cursor").fetchone()[0],1)
    def test_expired_lease_cannot_write(self):
        self.acquire(expiry=self.now-1)
        self.assertEqual(self.insert_cursor(),0)
    def test_valid_lease_allows_expected_update(self):
        self.acquire()
        self.assertEqual(self.insert_cursor(),1)
        self.assertEqual(self.update_cursor(),1)
        self.assertEqual(self.db.execute("SELECT generation FROM lbc_graph_delta_cursor").fetchone()[0],2)

if __name__=="__main__":
    unittest.main()
