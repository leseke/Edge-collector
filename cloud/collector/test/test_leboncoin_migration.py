"""SQLite negative/positive checks for the additive Outlook D1 migration."""
import pathlib
import sqlite3
import unittest

MIGRATION = pathlib.Path(__file__).resolve().parents[1] / "migrations" / "003_leboncoin_outlook.sql"


class LeboncoinLedgerTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(MIGRATION.read_text(encoding="utf-8"))

    def tearDown(self):
        self.db.close()

    def message(self):
        self.db.execute("""INSERT INTO lbc_alert_messages
            (message_id,received_at,search_name,advertised_count,extracted_count,truncated_email,ingested_at)
            VALUES ('mail-1','2026-11-19T05:21:31Z','Pokémon 30 ans',990,1,1,'2026-11-19T11:00:00Z')""")

    def listing(self):
        self.db.execute("""INSERT INTO lbc_listing_observations
            (message_id,listing_id,observed_at,source_url,title,price_cents,currency,location,category_hint)
            VALUES ('mail-1','leboncoin:3312500756','2026-11-19T05:21:31Z',
                    'https://www.leboncoin.fr/vi/3312500756.htm','Dracaufeu',16000,'EUR','France','Pokémon 30 ans')""")

    def test_immutable_evidence(self):
        self.message()
        self.listing()
        with self.assertRaisesRegex(sqlite3.DatabaseError,"immutable_lbc_listing"):
            self.db.execute("UPDATE lbc_listing_observations SET price_cents=1")
        with self.assertRaisesRegex(sqlite3.DatabaseError,"immutable_lbc_message"):
            self.db.execute("DELETE FROM lbc_alert_messages WHERE message_id='mail-1'")

    def test_idempotent_message_and_listing(self):
        self.message()
        self.listing()
        self.db.execute("""INSERT OR IGNORE INTO lbc_alert_messages
            (message_id,received_at,search_name,advertised_count,extracted_count,truncated_email,ingested_at)
            VALUES ('mail-1','2026-11-19T05:21:31Z','Pokémon 30 ans',990,1,1,'2026-11-19T11:00:00Z')""")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM lbc_alert_messages").fetchone()[0],1)

    def test_bad_sale_kind_and_negative_price(self):
        self.message()
        for kind,cents in (("COMPLETED_SALE",100),("LISTING",-1)):
            with self.assertRaises(sqlite3.IntegrityError):
                self.db.execute("""INSERT INTO lbc_listing_observations
                    (message_id,listing_id,observed_at,source_url,category_hint,price_kind,price_cents)
                    VALUES (?,?,?,?,?,?,?)""",("mail-1","leboncoin:1","2026-11-19T05:21:31Z",
                    "https://www.leboncoin.fr/vi/1.htm","Pokémon",kind,cents))

    def test_orphan_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("""INSERT INTO lbc_listing_observations
                (message_id,listing_id,observed_at,source_url,category_hint)
                VALUES ('unknown','leboncoin:1','2026-11-19T05:21:31Z',
                        'https://www.leboncoin.fr/vi/1.htm','Pokémon')""")


if __name__ == "__main__":
    unittest.main()
