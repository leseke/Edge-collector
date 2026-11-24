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

    def test_price_drop_query(self):
        db = sqlite3.connect(":memory:")
        self.addCleanup(db.close)
        db.executescript((ROOT / "migrations/003_gcc_offer_observations.sql").read_text())
        query = (ROOT.parents[1] / "app/lib/offer-price-signals.ts").read_text().split("priceDropQuery = `", 1)[1].split("`;", 1)[0]
        for lot, kind, pairs in [
            ("good","fixed",[(20000,"v"),(14000,"v")]),
            ("auction","auction",[(20000,"v"),(14000,"v")]),
            ("changed","fixed",[(20000,"v"),(14000,"w")]),
            ("unknown","fixed",[(20000,None),(14000,None)]),
            ("higher","fixed",[(10000,"v"),(14000,"v")]),
            ("missing","fixed",[(None,"v"),(14000,"v")]),
        ]:
            for i,(price,variant) in enumerate(pairs):
                db.execute("INSERT INTO gcc_offer_observations VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (kind,lot,f"2026-11-{23+i}T10:00:00.000Z",i+1,1,variant,lot,price,None,"https://example.com"))
        rows = db.execute(query,("2026-10-25T00:00:00.000Z","2026-11-24T16:00:00.000Z","2026-11-22T16:00:00.000Z")).fetchall()
        self.assertEqual([r[0] for r in rows],["good","unknown"])

if __name__ == "__main__":
    unittest.main()
