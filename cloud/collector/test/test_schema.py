"""Offline SQLite compatibility checks for the EDGE D1 schema.

Runs without Cloudflare credentials, network access or paid services.
SQLite compatibility is necessary but does not prove Cloudflare D1 integration.
"""
from pathlib import Path
import sqlite3
import unittest
import uuid

SCHEMA = Path(__file__).resolve().parents[1] / "schema.sql"


class CollectorSchemaTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA.read_text(encoding="utf-8"))

    def tearDown(self):
        self.db.close()

    def run_insert(self, run_id="run-1", status="RUNNING"):
        self.db.execute(
            "INSERT INTO collection_runs(run_id,started_at,status) VALUES(?,?,?)",
            (run_id, "2026-11-15T10:00:00Z", status),
        )

    def observe(self, observation_id, run_id, price=129, kind="AGGREGATE"):
        self.db.execute(
            """INSERT INTO observations(
              observation_id,run_id,product_id,source,observed_at,price_cents,
              currency,availability,price_kind,source_url,payload_sha256
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                observation_id, run_id, "pokemon_card_base1_4", "TCGdex/Cardmarket",
                "2026-11-15T10:00:01Z", price, "EUR", "UNKNOWN", kind,
                "https://api.tcgdex.net/v2/fr/cards/base1-4", "a" * 64,
            ),
        )

    def test_run_and_observation_are_persisted(self):
        self.run_insert()
        self.observe("obs-1", "run-1")
        self.db.execute(
            "UPDATE collection_runs SET finished_at=?,status=?,attempted=?,succeeded=?,failed=? WHERE run_id=?",
            ("2026-11-15T10:00:02Z", "OK", 1, 1, 0, "run-1"),
        )
        self.assertEqual(
            self.db.execute("SELECT status,attempted,succeeded,failed FROM collection_runs").fetchone(),
            ("OK", 1, 1, 0),
        )
        self.assertEqual(self.db.execute("SELECT price_cents,price_kind FROM observations").fetchone(), (129, "AGGREGATE"))

    def test_duplicate_observation_is_rejected(self):
        self.run_insert()
        self.observe("obs-1", "run-1")
        with self.assertRaises(sqlite3.IntegrityError):
            self.observe("obs-1", "run-1")

    def test_orphan_observation_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.observe("obs-orphan", "missing-run")

    def test_invalid_status_and_negative_price_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_insert("bad-run", "MAGIC")
        self.run_insert()
        with self.assertRaises(sqlite3.IntegrityError):
            self.observe("obs-negative", "run-1", -1)

    def test_observations_are_append_only(self):
        self.run_insert()
        self.observe("obs-1", "run-1")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE observations SET price_cents=999 WHERE observation_id='obs-1'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("DELETE FROM observations WHERE observation_id='obs-1'")
        self.assertEqual(self.db.execute("SELECT price_cents FROM observations").fetchone(), (129,))

    def test_two_runs_keep_separate_observations(self):
        self.run_insert("run-1")
        self.run_insert("run-2")
        self.observe("obs-1", "run-1", 129)
        self.observe("obs-2", "run-2", 159)
        self.assertEqual(
            self.db.execute("SELECT price_cents FROM observations ORDER BY price_cents").fetchall(),
            [(129,), (159,)],
        )


if __name__ == "__main__":
    unittest.main()
