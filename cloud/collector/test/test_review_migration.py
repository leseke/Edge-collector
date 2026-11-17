"""Offline review persistence contract tests; no D1 remote writes or network."""
from pathlib import Path
import sqlite3
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "schema.sql").read_text(encoding="utf-8")
MIGRATION = (ROOT / "migrations/002_investigation_review.sql").read_text(encoding="utf-8")
HASH = "a" * 64
NOW = "2026-11-17T18:00:00Z"


class ReviewMigrationTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(SCHEMA)
        self.db.executescript(MIGRATION)

    def tearDown(self):
        self.db.close()

    def investigation(self, id="inv1", status="PENDING_REVIEW", authorized=0):
        self.db.execute(
            "INSERT INTO investigations(investigation_id,product_id,created_at,evidence_snapshot_hash,proposal_json,status,purchase_authorized) VALUES(?,?,?,?,?,?,?)",
            (id, "pokemon_card_base1_4", NOW, HASH, '{"thesis":"preshot"}', status, authorized),
        )

    def decision(self, id="dec1", investigation="inv1", key="request-1", value="APPROVE", reviewer="reviewer1", authorized=0):
        self.db.execute(
            "INSERT INTO review_decisions(decision_id,investigation_id,reviewer_id,decision,rationale,decided_at,idempotency_key,purchase_authorized) VALUES(?,?,?,?,?,?,?,?)",
            (id, investigation, reviewer, value, "Reviewed evidence", NOW, key, authorized),
        )

    def event(self, id="event1", investigation="inv1", kind="INVESTIGATION_CREATED"):
        self.db.execute(
            "INSERT INTO investigation_audit_events(event_id,investigation_id,actor_id,event_type,occurred_at,payload_hash) VALUES(?,?,?,?,?,?)",
            (id, investigation, "reviewer1", kind, NOW, HASH),
        )

    def test_migration_reentrant_and_original_tables_preserved(self):
        self.db.executescript(MIGRATION)
        self.assertTrue({"observations", "collection_runs", "collection_errors", "investigations", "review_decisions", "investigation_audit_events"}.issubset(
            {r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        ))

    def test_review_is_immutable_and_never_authorizes_purchase(self):
        self.investigation()
        self.decision()
        self.event()
        for sql in (
            "UPDATE investigations SET product_id='other'",
            "DELETE FROM investigations",
            "UPDATE review_decisions SET decision='REJECT'",
            "DELETE FROM review_decisions",
            "UPDATE investigation_audit_events SET event_type='REVIEW_APPROVED'",
            "DELETE FROM investigation_audit_events",
        ):
            with self.subTest(sql=sql), self.assertRaises(sqlite3.IntegrityError):
                self.db.execute(sql)
        self.assertEqual(self.db.execute("SELECT decision,purchase_authorized FROM review_decisions").fetchone(), ("APPROVE", 0))

    def test_duplicate_decision_and_reused_idempotency_key_rejected(self):
        self.investigation()
        self.investigation("inv2")
        self.decision()
        with self.assertRaises(sqlite3.IntegrityError):
            self.decision("dec2", "inv1", "request-2")
        with self.assertRaises(sqlite3.IntegrityError):
            self.decision("dec3", "inv2", "request-1")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM review_decisions").fetchone()[0], 1)

    def test_orphans_and_missing_reviewer_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.decision(investigation="missing")
        with self.assertRaises(sqlite3.IntegrityError):
            self.event(investigation="missing")
        self.investigation()
        with self.assertRaises(sqlite3.IntegrityError):
            self.decision(reviewer="  ")

    def test_invalid_status_decision_json_hash_and_purchase_flag_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.investigation(status="APPROVED")
        with self.assertRaises(sqlite3.IntegrityError):
            self.investigation(authorized=1)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO investigations(investigation_id,product_id,created_at,evidence_snapshot_hash,proposal_json) VALUES(?,?,?,?,?)",
                            ("bad", "product", NOW, HASH, "not json"))
        self.investigation()
        with self.assertRaises(sqlite3.IntegrityError):
            self.decision(value="BUY")
        with self.assertRaises(sqlite3.IntegrityError):
            self.decision(authorized=1)
        with self.assertRaises(sqlite3.IntegrityError):
            self.event(kind="PURCHASE_EXECUTED")

    def test_existing_observations_stay_immutable(self):
        self.db.execute("INSERT INTO collection_runs(run_id,started_at,status) VALUES(?,?,?)", ("run", NOW, "RUNNING"))
        self.db.execute("INSERT INTO observations(observation_id,run_id,product_id,source,observed_at,price_kind,source_url,payload_sha256) VALUES(?,?,?,?,?,?,?,?)",
                        ("obs", "run", "product", "source", NOW, "AGGREGATE", "https://example.com", HASH))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("DELETE FROM observations WHERE observation_id='obs'")


if __name__ == "__main__":
    unittest.main()
