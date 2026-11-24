import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class OfferHistoryTests(unittest.TestCase):
    def test_additive_migration_and_immutable_history(self):
        db = sqlite3.connect(":memory:")
        self.addCleanup(db.close)
        migration = (ROOT / "migrations/003_gcc_offer_observations.sql").read_text()
        db.executescript(migration)
        db.executescript(migration)
        sql = """INSERT OR IGNORE INTO gcc_offer_observations
          (kind,lot_id,observed_at,cycle,page,variant_key,title,price_cents,ends_at,source_url)
          VALUES ('fixed','lot',?, ?,1,NULL,'Card',?,NULL,'https://gradedcardcenter.com/item/lot')"""
        db.execute(sql, ("2026-11-23T10:00:00Z",1,20000))
        db.execute(sql, ("2026-11-23T10:00:00Z",1,10000))
        db.execute(sql, ("2026-11-24T10:00:00Z",2,14000))
        self.assertEqual(db.execute("SELECT price_cents FROM gcc_offer_observations ORDER BY cycle").fetchall(), [(20000,), (14000,)])
        for query in ("UPDATE gcc_offer_observations SET price_cents=1", "DELETE FROM gcc_offer_observations"):
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(query)

if __name__ == "__main__":
    unittest.main()
