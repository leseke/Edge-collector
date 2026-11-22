"""Real SQLite verification of fenced OAuth credential writes."""
import pathlib
import sqlite3
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
OWNER="a"*64
LEASE="123e4567-e89b-12d3-a456-426614174000"

class OAuthFencingTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        for n in ("005_outlook_oauth_secure.sql","006_outlook_run_lease.sql"):
            self.db.executescript((ROOT/"migrations"/n).read_text(encoding="utf-8"))
    def tearDown(self):
        self.db.close()
    def insert(self):
        return self.db.execute("""INSERT OR IGNORE INTO lbc_oauth_credentials
          (mailbox_key,nonce_b64,ciphertext_b64,generation,modified_at)
          SELECT ?,?,?,1,? WHERE EXISTS
          (SELECT 1 FROM lbc_sync_lease WHERE owner_key=? AND lease_id=? AND expires_at_ms>?)""",
          (OWNER,"n","encrypted","2026-11-19T06:00:00Z",OWNER,LEASE,1000)).rowcount
    def update(self):
        return self.db.execute("""UPDATE lbc_oauth_credentials SET nonce_b64=?,
          ciphertext_b64=?,generation=generation+1,modified_at=?
          WHERE mailbox_key=? AND generation=? AND EXISTS
          (SELECT 1 FROM lbc_sync_lease WHERE owner_key=? AND lease_id=? AND expires_at_ms>?)""",
          ("n2","rotated","2026-11-19T06:01:00Z",OWNER,1,OWNER,LEASE,1000)).rowcount
    def lease(self,id=LEASE,expiry=2000):
        self.db.execute("INSERT OR REPLACE INTO lbc_sync_lease VALUES (?,?,?,?)",(OWNER,id,expiry,500))
    def test_no_lease_denies_initial_credentials(self):
        self.assertEqual(self.insert(),0)
    def test_expired_lease_denies_initial_credentials(self):
        self.lease(expiry=900)
        self.assertEqual(self.insert(),0)
    def test_valid_lease_can_insert_and_rotate(self):
        self.lease()
        self.assertEqual(self.insert(),1)
        self.assertEqual(self.update(),1)
        self.assertEqual(self.db.execute("SELECT generation FROM lbc_oauth_credentials").fetchone()[0],2)
    def test_replaced_lease_denies_refresh_rotation(self):
        self.lease()
        self.assertEqual(self.insert(),1)
        self.lease(id="b"*36)
        self.assertEqual(self.update(),0)
        self.assertEqual(self.db.execute("SELECT ciphertext_b64 FROM lbc_oauth_credentials").fetchone()[0],"encrypted")

if __name__=="__main__":
    unittest.main()
