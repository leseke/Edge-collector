"""Compatibility and constraints tests for encrypted OAuth D1 schema."""
import pathlib
import sqlite3
import unittest

MIGRATION=pathlib.Path(__file__).resolve().parents[1]/"migrations"/"005_outlook_oauth_secure.sql"

class OAuthSchemaTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.executescript(MIGRATION.read_text(encoding="utf-8"))
    def tearDown(self):
        self.db.close()
    def test_one_time_pending_state_returning(self):
        state="A"*43
        self.db.execute("""INSERT INTO lbc_oauth_pending
        (state_hash,ciphertext_b64,nonce_b64,expires_at,created_at)
        VALUES (?,?,?,?,?)""",(state,"cipher","nonce",600000,"2026-11-19T00:00:00Z"))
        consumed=self.db.execute("""DELETE FROM lbc_oauth_pending
          WHERE state_hash=? RETURNING nonce_b64,ciphertext_b64,expires_at""",(state,)).fetchone()
        self.assertEqual(consumed,("nonce","cipher",600000))
        self.assertIsNone(self.db.execute("""DELETE FROM lbc_oauth_pending
          WHERE state_hash=? RETURNING nonce_b64,ciphertext_b64,expires_at""",(state,)).fetchone())
    def test_credential_compare_and_swap(self):
        key="1"*32
        self.db.execute("""INSERT INTO lbc_oauth_credentials
          (mailbox_key,nonce_b64,ciphertext_b64,generation,modified_at)
          VALUES (?,?,?,?,?)""",(key,"nonce","cipher",1,"2026-11-19T00:00:00Z"))
        updated=self.db.execute("""UPDATE lbc_oauth_credentials SET nonce_b64=?,
          ciphertext_b64=?,generation=generation+1,modified_at=?
          WHERE mailbox_key=? AND generation=?""",("newnonce","newcipher","2026-11-19T00:00:01Z",key,1))
        self.assertEqual(updated.rowcount,1)
        stale=self.db.execute("""UPDATE lbc_oauth_credentials SET nonce_b64=?,
          ciphertext_b64=?,generation=generation+1,modified_at=?
          WHERE mailbox_key=? AND generation=?""",("bad","bad","2026-11-19T00:00:02Z",key,1))
        self.assertEqual(stale.rowcount,0)
        self.assertEqual(self.db.execute("SELECT generation FROM lbc_oauth_credentials").fetchone()[0],2)

if __name__=="__main__":
    unittest.main()
