"""End-to-end local history probe using the exact D1-compatible schema.

No network, credentials or real prices. All sample observations are fixtures,
never production evidence. This validates storage and chronological comparisons,
not Cloudflare's deployed D1 API or a real upstream response.
"""
import sqlite3
import unittest
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1] / "schema.sql"


def record_run(db, run_id, at, observation_id, price_cents):
    db.execute(
        "INSERT INTO collection_runs(run_id,started_at,status) VALUES(?,?,?)",
        (run_id, at, "RUNNING"),
    )
    db.execute(
        """INSERT INTO observations(
          observation_id,run_id,product_id,source,observed_at,price_cents,
          currency,availability,price_kind,source_url,payload_sha256
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            observation_id, run_id, "probe-card", "FIXTURE_ONLY", at, price_cents,
            "EUR", "UNKNOWN", "AGGREGATE", "https://example.invalid/fixture",
            "a" * 64,
        ),
    )
    db.execute(
        "UPDATE collection_runs SET finished_at=?,status=?,attempted=1,succeeded=1,failed=0 WHERE run_id=?",
        (at, "OK", run_id),
    )


class HistoryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(SCHEMA.read_text(encoding="utf-8"))

    def tearDown(self):
        self.db.close()

    def test_two_collection_runs_preserve_change_and_provenance(self):
        record_run(self.db, "run-a", "2026-11-15T08:00:00Z", "obs-a", 200)
        record_run(self.db, "run-b", "2026-11-15T09:00:00Z", "obs-b", 150)
        rows = self.db.execute(
            """SELECT price_cents,price_kind,source,observed_at
               FROM observations WHERE product_id=? ORDER BY observed_at ASC""",
            ("probe-card",),
        ).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertEqual([r[0] for r in rows], [200, 150])
        self.assertEqual(rows[-1][0] - rows[0][0], -50)
        self.assertTrue(all(r[1] == "AGGREGATE" for r in rows))
        self.assertTrue(all(r[2] == "FIXTURE_ONLY" for r in rows))
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM collection_runs WHERE status='OK'").fetchone()[0],
            2,
        )

    def test_empty_run_does_not_invent_observation(self):
        self.db.execute(
            "INSERT INTO collection_runs(run_id,started_at,finished_at,status,attempted,succeeded,failed) VALUES (?,?,?,?,?,?,?)",
            ("run-empty", "2026-11-15T10:00:00Z", "2026-11-15T10:00:01Z", "EMPTY", 0, 0, 0),
        )
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
