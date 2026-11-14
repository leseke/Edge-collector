import os
import tempfile
import unittest
from unittest import mock

import storage
from intelligence.continuity_pipeline import build_local_sqlite_continuity_report
from connectors.result import completed_query, failed_query
from intelligence.scheduled_run_context import ScheduledRunContext
from intelligence.sqlite_continuity_journal import SQLiteContinuityJournal


SCHEDULED = "2026-11-03T01:00:00Z"
STARTED_AT = "2026-11-03T01:00:03Z"
RESULT_AT = "2026-11-03T01:01:00Z"
FINISHED_AT = "2026-11-03T01:02:00Z"
WINDOW = {
    "window_id": "hourly:20261103T010000Z",
    "scheduled_at": SCHEDULED,
    "expected_sources": ["source-a", "source-b"],
}


class SQLiteContinuityJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "test.db")
        self.db_patch = mock.patch.object(storage, "DB", self.db_path)
        self.db_patch.start()
        storage.init_db().close()
        self.journal = SQLiteContinuityJournal(
            storage.append_run_event, storage.list_run_events,
            storage.list_all_run_events,
        )
        self.context = ScheduledRunContext(
            window_id=WINDOW["window_id"], scheduled_at=SCHEDULED,
            run_id="scheduled-run-attempt-1", attempt=1,
            expected_sources=tuple(WINDOW["expected_sources"]),
        )

    def tearDown(self):
        self.db_patch.stop()
        self.tmp.cleanup()

    def test_complete_lifecycle_writes_only_allowlisted_events(self):
        self.journal.start(self.context, [WINDOW], occurred_at=STARTED_AT)
        self.journal.record_source_result(
            self.context, [WINDOW], completed_query(3), "source-a", RESULT_AT
        )
        self.journal.record_source_result(
            self.context, [WINDOW], completed_query(0), "source-b",
            "2026-11-03T01:01:30Z"
        )
        self.journal.finish(self.context, {
            "run_status": "OK", "sources_expected": ["source-a", "source-b"],
            "sources_failed": [], "collected_records": 3,
            "product_price_snapshots": 0, "retail_offer_batches": 0,
        }, FINISHED_AT)
        rows = storage.list_run_events(self.context.run_id)
        self.assertEqual([row["event_type"] for row in rows],
                         ["STARTED", "SOURCE_RESULT", "SOURCE_RESULT", "FINISHED"])
        self.assertEqual(rows[0]["payload"], {
            "trigger": "schedule", "scheduled_at": SCHEDULED,
        })
        self.assertEqual(rows[1]["payload"], {
            "window_id": WINDOW["window_id"], "source_id": "source-a",
            "outcome": "OBSERVED",
        })
        self.assertEqual(rows[2]["payload"]["outcome"], "NO_REACTION_OBSERVED")

    def test_local_sqlite_history_replays_but_never_claims_durable_coverage(self):
        context = ScheduledRunContext(
            window_id="pipeline-hourly:20261103T010000Z",
            scheduled_at=SCHEDULED, run_id="sqlite-report-run-attempt-1",
            attempt=1, expected_sources=("check-a", "check-b"),
        )
        window = {
            "window_id": context.window_id,
            "scheduled_at": SCHEDULED,
            "expected_sources": ["check-a", "check-b"],
        }
        self.journal.start(context, [window], occurred_at=STARTED_AT)
        self.journal.record_source_result(
            context, [window], completed_query(2), "check-a", RESULT_AT
        )
        self.journal.record_source_result(
            context, [window], completed_query(0), "check-b",
            "2026-11-03T01:01:30Z",
        )
        self.journal.finish(context, {
            "run_status": "OK", "sources_expected": ["check-a", "check-b"],
            "sources_failed": [], "collected_records": 2,
            "product_price_snapshots": 1, "retail_offer_batches": 0,
        }, FINISHED_AT)

        report = build_local_sqlite_continuity_report(
            {
                "schedule_id": "pipeline-hourly", "timezone": "UTC",
                "interval_minutes": 60, "lookback_days": 0,
            },
            {
                "expected_sources": ["check-a", "check-b"],
                "not_scheduled_sources": [],
                "providers": {"check-a": "ebay", "check-b": "cardmarket"},
            },
            "2026-11-03T02:00:00Z",
            self.journal,
        )
        row = next(item for item in report["windows"]
                   if item["window_id"] == context.window_id)
        self.assertEqual(row["status"], "OBSERVED")
        self.assertEqual(report["source_counts"]["NO_REACTION_OBSERVED"], 1)
        self.assertEqual(report["journal_backend"], "SQLITE_LOCAL")
        self.assertEqual(report["journal_status"], "DEGRADED")
        self.assertEqual(report["continuity_status"], "UNKNOWN")
        self.assertEqual(report["unknown_reason"], "LOCAL_SQLITE_HISTORY_NOT_DURABLE")
        self.assertIsNone(report["observation_coverage_ratio"])
        self.assertGreater(report["window_counts"]["UNKNOWN"], 0)

    def test_duplicate_identical_source_result_is_idempotent(self):
        self.journal.start(self.context, [WINDOW], occurred_at=STARTED_AT)
        self.journal.record_source_result(
            self.context, [WINDOW], completed_query(1), "source-a", RESULT_AT
        )
        # The underlying SQLite journal treats identical (window, source) as a no-op.
        self.journal.record_source_result(
            self.context, [WINDOW], completed_query(1), "source-a", RESULT_AT
        )
        rows = storage.list_run_events(self.context.run_id)
        self.assertEqual(sum(row["event_type"] == "SOURCE_RESULT" for row in rows), 1)

    def test_conflicting_duplicate_source_result_is_rejected(self):
        self.journal.start(self.context, [WINDOW], occurred_at=STARTED_AT)
        self.journal.record_source_result(
            self.context, [WINDOW], completed_query(1), "source-a", RESULT_AT
        )
        with self.assertRaisesRegex(ValueError, "différent"):
            self.journal.record_source_result(
                self.context, [WINDOW], completed_query(0), "source-a", RESULT_AT
            )

    def test_source_result_cannot_be_written_before_start(self):
        with self.assertRaisesRegex(ValueError, "no verified STARTED"):
            self.journal.record_source_result(
                self.context, [WINDOW], completed_query(1), "source-a", RESULT_AT
            )

    def test_unexpected_source_is_rejected_without_journal_write(self):
        self.journal.start(self.context, [WINDOW], occurred_at=STARTED_AT)
        with self.assertRaisesRegex(ValueError, "not expected"):
            self.journal.record_source_result(
                self.context, [WINDOW], completed_query(1), "source-z", RESULT_AT
            )
        self.assertEqual(len(storage.list_run_events(self.context.run_id)), 1)

    def test_source_failure_records_only_safe_outcome(self):
        self.journal.start(self.context, [WINDOW], occurred_at=STARTED_AT)
        self.journal.record_source_result(
            self.context, [WINDOW], failed_query(RuntimeError("secret payload")),
            "source-a", RESULT_AT
        )
        payload = storage.list_run_events(self.context.run_id)[1]["payload"]
        self.assertEqual(payload["outcome"], "SOURCE_FAILED")
        self.assertNotIn("secret payload", repr(payload))
        self.assertEqual(set(payload), {"window_id", "source_id", "outcome"})

    def test_finish_requires_start_and_valid_run_status(self):
        with self.assertRaisesRegex(ValueError, "exactly one prior STARTED"):
            self.journal.finish(self.context, {"run_status": "OK"}, FINISHED_AT)
        self.journal.start(self.context, [WINDOW], occurred_at=STARTED_AT)
        with self.assertRaisesRegex(ValueError, "valid run_status"):
            self.journal.finish(self.context, {"run_status": "UNKNOWN"}, FINISHED_AT)

    def test_manual_run_cannot_be_claimed_by_scheduled_context(self):
        storage.append_run_event(self.context.run_id, "STARTED", {
            "trigger": "workflow_dispatch", "scheduled_at": None,
        }, STARTED_AT)
        with self.assertRaisesRegex(ValueError, "explicit scheduled_at"):
            self.journal.record_source_result(
                self.context, [WINDOW], completed_query(1), "source-a", RESULT_AT
            )

    def test_start_rejects_manual_trigger(self):
        with self.assertRaisesRegex(ValueError, "schedule trigger"):
            self.journal.start(self.context, [WINDOW], trigger="workflow_dispatch")

    def test_start_rejects_context_not_present_in_expected_schedule(self):
        wrong_window = [{**WINDOW, "window_id": "another-window"}]
        with self.assertRaisesRegex(ValueError, "exactly one expected window"):
            self.journal.start(self.context, wrong_window, occurred_at=STARTED_AT)
        self.assertEqual(storage.list_run_events(self.context.run_id), [])



if __name__ == "__main__":
    unittest.main()
