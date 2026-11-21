"""Real SQLite checks for leased Outlook message and listing inserts."""
import pathlib
import sqlite3
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
OWNER="a"*64
LEASE="123e4567-e89b-12d3-a456-426614174000"

class ObservationFencingTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("PRAGMA foreign_keys=ON")
        for n in ("003_leboncoin_outlook.sql","006_outlook_run_lease.sql"):
            self.db.executescript((ROOT/"migrations"/n).read_text(encoding="utf-8"))
        self.now=1000000
    def tearDown(self):
        self.db.close()
    def insert_lease(self,lease=LEASE,expiry=2000000):
        self.db.execute("""INSERT INTO lbc_sync_lease
            (owner_key,lease_id,expires_at_ms,acquired_at_ms) VALUES (?,?,?,?)""",
            (OWNER,lease,expiry,self.now))
    def add_alert(self):
        return self.db.execute("""INSERT OR IGNORE INTO lbc_alert_messages
        (message_id,received_at,search_name,advertised_count,extracted_count,truncated_email,ingested_at)
        SELECT ?,?,?,?,?,?,? WHERE EXISTS
        (SELECT 1 FROM lbc_sync_lease WHERE owner_key=? AND lease_id=? AND expires_at_ms>?)""",
        ("mail-1","2026-11-19T05:21:31Z","Pokémon",1,1,0,"2026-11-19T06:00:00Z",
         OWNER,LEASE,self.now)).rowcount
    def add_listing(self):
        return self.db.execute("""INSERT OR IGNORE INTO lbc_listing_observations
          (message_id,listing_id,observed_at,source_url,title,price_cents,currency,
           location,category_hint,price_kind,availability,evidence)
          SELECT ?,?,?,?,?,?,?,?,?,?,?,? WHERE EXISTS
          (SELECT 1 FROM lbc_alert_messages WHERE message_id=? AND ingested_at=?)
          AND EXISTS (SELECT 1 FROM lbc_sync_lease
           WHERE owner_key=? AND lease_id=? AND expires_at_ms>?)""",
          ("mail-1","leboncoin:3312468604","2026-11-19T05:21:31Z",
           "https://www.leboncoin.fr/vi/3312468604.htm","ETB Pokémon",7500,"EUR",
           "Évreux","Pokémon","LISTING","UNVERIFIED","EMAIL_EXCERPT",
           "mail-1","2026-11-19T06:00:00Z",OWNER,LEASE,self.now)).rowcount
    def test_missing_lease_blocks_alert_and_listing(self):
        self.assertEqual(self.add_alert(),0)
        self.assertEqual(self.add_listing(),0)
    def test_expired_lease_blocks_alert(self):
        self.insert_lease(expiry=self.now-1)
        self.assertEqual(self.add_alert(),0)
    def test_valid_lease_writes_both(self):
        self.insert_lease()
        with self.db:
            self.assertEqual(self.add_alert(),1)
            self.assertEqual(self.add_listing(),1)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM lbc_listing_observations").fetchone()[0],1)
    def test_replacement_lease_refuses_stale_worker(self):
        self.insert_lease(lease="b"*36)
        self.assertEqual(self.add_alert(),0)
        self.assertEqual(self.add_listing(),0)

if __name__=="__main__":
    unittest.main()
