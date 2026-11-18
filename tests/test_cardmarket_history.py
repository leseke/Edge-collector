import sqlite3
import unittest
from datetime import date, timedelta

from scripts.cardmarket_history import compare_history, coverage, import_guide


def snapshot(day, amount, checksum=None):
    return {
        "guide": ({
            "createdAt": day + "T01:00:00+01:00",
            "priceGuides": [
                {"idProduct": 1, "idCategory": 51, "trend": amount, "trend-holo": 400},
                {"idProduct": 2, "idCategory": 1015, "trend": 50},
                {"idProduct": 3, "idCategory": 52, "trend": 60},
                {"idProduct": 4, "idCategory": 52, "trend": 1},
            ],
        }, checksum or day),
        "singles": ({"products": [{"idProduct": 1, "idCategory": 51, "name": "Card"}]}, "singles"),
        "sealed": ({"products": [
            {"idProduct": 2, "idCategory": 1015, "name": "Box"},
            {"idProduct": 3, "idCategory": 52, "name": "Booster"},
            {"idProduct": 4, "idCategory": 53, "name": "Display"},
        ]}, "sealed"),
    }


class CardmarketHistoryTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.now = date(2026, 11, 18)

    def tearDown(self):
        self.db.close()

    def test_source_day_is_unique_and_catalog_identity_and_finish_stay_distinct(self):
        day = self.now.isoformat()
        documents = snapshot(day, 100)
        self.assertEqual(import_guide(self.db, documents, self.now), (day, True))
        self.assertEqual(import_guide(self.db, documents, self.now), (day, False))
        self.assertEqual(coverage(self.db, day)["CARTE"], {"products": 1, "quotes": 2})
        self.assertNotIn("DISPLAY", coverage(self.db, day))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM guide_prices").fetchone()[0], 4)
        with self.assertRaisesRegex(ValueError, "conflicting_same_day_guide"):
            import_guide(self.db, snapshot(day, 300, "changed"), self.now)
        with self.assertRaisesRegex(ValueError, "invalid_guide_date"):
            import_guide(self.db, snapshot("2026-11-19", 300), self.now)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM guide_days").fetchone()[0], 1)

    def test_disjoint_windows_require_seven_unique_days_each(self):
        day = self.now.isoformat()
        for offset in (*range(7), *range(30, 36)):
            current = self.now - timedelta(days=offset)
            import_guide(self.db, snapshot(current.isoformat(), 120 if offset < 30 else 100), self.now)
        self.assertEqual(compare_history(self.db, 1, "STANDARD", day), {
            "recent_days": 7, "prior_days": 6, "change_pct": None,
        })
        extra = self.now - timedelta(days=36)
        import_guide(self.db, snapshot(extra.isoformat(), 100), self.now)
        self.assertEqual(compare_history(self.db, 1, "STANDARD", day)["change_pct"], 20)
        self.assertEqual(compare_history(self.db, 1, "HOLO", day)["change_pct"], 0)
        self.assertEqual(compare_history(self.db, 2, "SEALED", day)["change_pct"], 0)
