"""Real SQLite verification of immutable Outlook replay completeness lookup."""
import pathlib
import sqlite3
import unittest

MIGRATION=pathlib.Path(__file__).resolve().parents[1]/"migrations"/"003_leboncoin_outlook.sql"
MESSAGE="mail-old"
LISTING="leboncoin:3312500756"

class ImmutableReplayIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(MIGRATION.read_text(encoding="utf-8"))
        self.db.execute("""INSERT INTO lbc_alert_messages
          (message_id,received_at,search_name,advertised_count,extracted_count,truncated_email,ingested_at)
          VALUES (?,?,?,?,?,?,?)""",(MESSAGE,"2026-11-19T05:21:31Z","Pokemon",1,1,0,
            "2026-11-19T06:00:00Z"))
        self.db.commit()
    def tearDown(self):
        self.db.close()
    def inspect(self,ids):
        matching=("""(SELECT COUNT(*) FROM lbc_listing_observations o
          WHERE o.message_id=m.message_id AND o.listing_id IN
          ("""+",".join("?" for _ in ids)+"))") if ids else "0"
        return self.db.execute("""SELECT m.extracted_count AS expected_count,
          (SELECT COUNT(*) FROM lbc_listing_observations o WHERE o.message_id=m.message_id)
            AS actual_count, """+matching+"""
          AS matching_count FROM lbc_alert_messages m WHERE m.message_id=? LIMIT 1""",
          (*ids,MESSAGE)).fetchone()
    def add(self,id):
        self.db.execute("""INSERT INTO lbc_listing_observations
          (message_id,listing_id,observed_at,source_url,category_hint,price_kind,availability,evidence)
          VALUES (?,?,?,?,?,?,?,?)""",(MESSAGE,id,"2026-11-19T05:21:31Z",
          "https://www.leboncoin.fr/vi/3312500756.htm","Pokemon","LISTING","UNVERIFIED","EMAIL_EXCERPT"))
        self.db.commit()
    def test_old_message_missing_listing_detected(self):
        self.assertEqual(self.inspect([LISTING]),(1,0,0))
    def test_complete_message_passes(self):
        self.add(LISTING)
        self.assertEqual(self.inspect([LISTING]),(1,1,1))
    def test_same_count_but_different_id_detected(self):
        self.add(LISTING)
        self.assertEqual(self.inspect(["leboncoin:3312500757"]),(1,1,0))
    def test_empty_message_with_zero_extracted_count(self):
        self.db.execute("""INSERT INTO lbc_alert_messages
          (message_id,received_at,search_name,advertised_count,extracted_count,truncated_email,ingested_at)
          VALUES (?,?,?,?,?,?,?)""",("empty","2026-11-19T05:21:31Z","Pokemon",0,0,0,
          "2026-11-19T06:00:00Z"))
        row=self.db.execute("""SELECT extracted_count,
          (SELECT COUNT(*) FROM lbc_listing_observations WHERE message_id=?) FROM lbc_alert_messages WHERE message_id=?""",
          ("empty","empty")).fetchone()
        self.assertEqual(row,(0,0))

if __name__=="__main__":
    unittest.main()
