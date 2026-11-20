"""Real SQLite proof: incomplete Outlook listing batches must roll back the mail row."""
import pathlib
import sqlite3
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
OWNER="a"*64
LEASE="123e4567-e89b-12d3-a456-426614174000"
NEW_LEASE="b"*36
WHEN=1000000

class OutlookBatchRollbackTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("PRAGMA foreign_keys=ON")
        for file in ("003_leboncoin_outlook.sql","006_outlook_run_lease.sql"):
            self.db.executescript((ROOT/"migrations"/file).read_text(encoding="utf-8"))
        self.db.execute("""INSERT INTO lbc_sync_lease
            (owner_key,lease_id,expires_at_ms,acquired_at_ms) VALUES (?,?,?,?)""",
            (OWNER,LEASE,WHEN+500000,WHEN))
        self.db.commit()
    def tearDown(self):
        self.db.close()
    def alert(self):
        return self.db.execute("""INSERT OR IGNORE INTO lbc_alert_messages
            (message_id,received_at,search_name,advertised_count,extracted_count,truncated_email,ingested_at)
            SELECT ?,?,?,?,?,?,? WHERE EXISTS (
              SELECT 1 FROM lbc_sync_lease WHERE owner_key=? AND lease_id=? AND expires_at_ms>?)""",
            ("mail-001","2026-11-20T07:00:00Z","Pokemon",2,2,0,
             "2026-11-20T07:01:00Z",OWNER,LEASE,WHEN)).rowcount
    def listing(self,number):
        return self.db.execute("""INSERT OR IGNORE INTO lbc_listing_observations
            (message_id,listing_id,observed_at,source_url,title,price_cents,
             currency,location,category_hint,price_kind,availability,evidence)
            SELECT ?,?,?,?,?,?,?,?,?,?,?,? WHERE EXISTS (
              SELECT 1 FROM lbc_alert_messages WHERE message_id=? AND ingested_at=?) AND EXISTS (
              SELECT 1 FROM lbc_sync_lease WHERE owner_key=? AND lease_id=? AND expires_at_ms>?)""",
            ("mail-001","leboncoin:"+str(number),"2026-11-20T07:00:00Z",
             "https://www.leboncoin.fr/vi/"+str(number)+".htm","Fixture",3000,
             "EUR",None,"Pokemon","LISTING","UNVERIFIED","EMAIL_EXCERPT",
             "mail-001","2026-11-20T07:01:00Z",OWNER,LEASE,WHEN)).rowcount
    def assert_complete_or_abort(self):
        return self.db.execute("""INSERT INTO lbc_alert_messages
            (message_id,received_at,search_name,advertised_count,extracted_count,truncated_email,ingested_at)
            SELECT ?,?,?,-1,0,0,? WHERE
            NOT EXISTS (SELECT 1 FROM lbc_alert_messages WHERE message_id=? AND ingested_at=?)
            OR (SELECT COUNT(*) FROM lbc_listing_observations WHERE message_id=?)<>?""",
            ("mail-001","2026-11-20T07:00:00Z","Pokemon",
             "2026-11-20T07:01:00Z","mail-001","2026-11-20T07:01:00Z",
             "mail-001",2)).rowcount
    def row_counts(self):
        return [self.db.execute("SELECT COUNT(*) FROM "+name).fetchone()[0]
                for name in ("lbc_alert_messages","lbc_listing_observations")]
    def test_successful_batch_commits_both_listings(self):
        with self.db:
            self.assertEqual(self.alert(),1)
            self.assertEqual(self.listing(3312468604),1)
            self.assertEqual(self.listing(3312468605),1)
            self.assertEqual(self.assert_complete_or_abort(),0)
        self.assertEqual(self.row_counts(),[1,2])
    def test_lost_lease_between_writes_rolls_back_message_and_listing(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db:
                self.assertEqual(self.alert(),1)
                self.assertEqual(self.listing(3312468604),1)
                # Another owner replaces this lease before the next statement.
                self.db.execute("UPDATE lbc_sync_lease SET lease_id=? WHERE owner_key=?",
                                (NEW_LEASE,OWNER))
                self.assertEqual(self.listing(3312468605),0)
                self.assert_complete_or_abort()
        self.assertEqual(self.row_counts(),[0,0])
        self.assertEqual(self.db.execute(
            "SELECT lease_id FROM lbc_sync_lease WHERE owner_key=?",(OWNER,)).fetchone()[0],LEASE)
    def test_missing_listing_rejects_batch_even_if_lease_is_still_held(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db:
                self.assertEqual(self.alert(),1)
                self.assertEqual(self.listing(3312468604),1)
                self.assert_complete_or_abort()
        self.assertEqual(self.row_counts(),[0,0])

if __name__=="__main__":
    unittest.main()
