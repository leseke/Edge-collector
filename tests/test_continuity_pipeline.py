import unittest
from datetime import datetime, timedelta

from intelligence.continuity_pipeline import build_continuity_report
from intelligence.remote_journal_simulator import make_event


PLAN = {
    "expected_sources": ["check-a", "check-b"],
    "not_scheduled_sources": ["disabled-c"],
    "providers": {
        "check-a": "ebay",
        "check-b": "cardmarket",
        "disabled-c": "reddit",
    },
}
CADENCE = {
    "schedule_id": "pipeline-hourly",
    "timezone": "UTC",
    "interval_minutes": 60,
    "lookback_days": 0,
}
AS_OF = "2026-11-03T02:00:00Z"


def events_for(run_id, scheduled_at, source_ids, outcomes=None):
    started = make_event(run_id, 1, "STARTED", scheduled_at, {
        "trigger": "schedule", "scheduled_at": scheduled_at,
    })
    result_events = []
    outcomes = outcomes or {}
    for index, source_id in enumerate(source_ids, start=1):
        occurred = (
            datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
            + timedelta(minutes=index)
        ).isoformat().replace("+00:00", "Z")
        result_events.append(make_event(run_id, 1, "SOURCE_RESULT", occurred, {
            "window_id": f"pipeline-hourly:{scheduled_at.replace('-', '').replace(':', '')}",
            "source_id": source_id,
            "outcome": outcomes.get(source_id, "OBSERVED"),
        }))
    completed = (
        datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
        + timedelta(minutes=10)
    ).isoformat().replace("+00:00", "Z")
    finished = make_event(run_id, 1, "FINISHED", completed, {
        "run_status": "OK", "sources_expected": source_ids,
        "sources_failed": [], "collected_records": 1,
        "product_price_snapshots": 1, "retail_offer_batches": 0,
        "started_at": scheduled_at, "completed_at": completed,
    })
    return [started, *result_events, finished]


class ContinuityPipelineTests(unittest.TestCase):
    def test_missing_cadence_stays_unknown_and_has_no_ratios(self):
        result = build_continuity_report(None, PLAN, AS_OF, [])
        self.assertEqual(result["schedule_status"], "UNKNOWN")
        self.assertEqual(result["continuity_status"], "UNKNOWN")
        self.assertEqual(result["unknown_reason"], "CADENCE_NOT_CONFIGURED")
        self.assertEqual(result["expected_windows"], 0)
        self.assertIsNone(result["observation_coverage_ratio"])
        self.assertIsNone(result["attempt_coverage_ratio"])

    def test_disabled_sources_are_excluded_from_expected_checks(self):
        result = build_continuity_report(CADENCE, PLAN, AS_OF, [])
        self.assertEqual(result["schedule_status"], "SCHEDULED")
        self.assertEqual(result["not_scheduled_sources"], ["disabled-c"])
        self.assertTrue(all(
            row["expected_sources"] == ["check-a", "check-b"]
            for row in result["windows"]
        ))
        self.assertEqual(result["expected_source_checks"], 6)

    def test_source_check_ids_can_be_mapped_to_connector_source_ids(self):
        mapping = {"check-a": "ebay:product-a", "check-b": "cardmarket:product-b"}
        result = build_continuity_report(
            CADENCE, PLAN, AS_OF, [], source_id_map=mapping
        )
        self.assertEqual(
            result["windows"][0]["missing_sources"],
            ["cardmarket:product-b", "ebay:product-a"],
        )

    def test_unlinked_real_run_is_not_misreported_as_missed(self):
        unscheduled = make_event("manual-run", 1, "STARTED", "2026-11-03T01:05:00Z", {
            "trigger": "workflow_dispatch", "scheduled_at": None,
        })
        result = build_continuity_report(CADENCE, PLAN, AS_OF, [unscheduled])
        self.assertEqual(result["continuity_status"], "UNKNOWN")
        self.assertEqual(result["unknown_reason"], "UNLINKED_RUN_HISTORY")
        self.assertEqual(result["window_counts"]["MISSED"], 0)
        self.assertGreater(result["window_counts"]["UNKNOWN"], 0)
        self.assertIsNone(result["observation_coverage_ratio"])
        self.assertIsNone(result["attempt_coverage_ratio"])

    def test_out_of_horizon_unlinked_run_does_not_poison_current_schedule(self):
        old = make_event("old-manual-run", 1, "STARTED", "2026-11-01T01:05:00Z", {
            "trigger": "workflow_dispatch", "scheduled_at": None,
        })
        result = build_continuity_report(CADENCE, PLAN, AS_OF, [old])
        self.assertEqual(result["continuity_status"], "GAP")
        self.assertEqual(result["window_counts"]["MISSED"], 2)
        self.assertNotIn("unknown_reason", result)

    def test_scheduled_run_with_complete_results_reconstructs(self):
        scheduled_at = "2026-11-03T01:00:00Z"
        window_id = "pipeline-hourly:20261103T010000Z"
        events = [
            make_event("run-1", 1, "STARTED", scheduled_at, {
                "trigger": "schedule", "scheduled_at": scheduled_at,
            }),
            make_event("run-1", 1, "SOURCE_RESULT", "2026-11-03T01:01:00Z", {
                "window_id": window_id, "source_id": "check-a", "outcome": "OBSERVED",
            }),
            make_event("run-1", 1, "SOURCE_RESULT", "2026-11-03T01:02:00Z", {
                "window_id": window_id, "source_id": "check-b",
                "outcome": "NO_REACTION_OBSERVED",
            }),
            make_event("run-1", 1, "FINISHED", "2026-11-03T01:10:00Z", {
                "run_status": "OK", "sources_expected": ["check-a", "check-b"],
                "sources_failed": [], "collected_records": 1,
                "product_price_snapshots": 1, "retail_offer_batches": 0,
                "started_at": scheduled_at, "completed_at": "2026-11-03T01:10:00Z",
            }),
        ]
        result = build_continuity_report(CADENCE, PLAN, AS_OF, events)
        row = next(item for item in result["windows"] if item["window_id"] == window_id)
        self.assertEqual(row["status"], "OBSERVED")
        self.assertEqual(result["window_counts"]["OBSERVED"], 1)
        self.assertEqual(result["source_counts"]["NO_REACTION_OBSERVED"], 1)
        self.assertIsNone(result["unknown_reason"])

    def test_unlinked_run_only_affects_windows_that_would_otherwise_be_missed(self):
        scheduled_at = "2026-11-03T01:00:00Z"
        window_id = "pipeline-hourly:20261103T010000Z"
        linked = [
            make_event("run-1", 1, "STARTED", scheduled_at, {
                "trigger": "schedule", "scheduled_at": scheduled_at,
            }),
            make_event("run-1", 1, "SOURCE_RESULT", "2026-11-03T01:01:00Z", {
                "window_id": window_id, "source_id": "check-a", "outcome": "OBSERVED",
            }),
            make_event("run-1", 1, "SOURCE_RESULT", "2026-11-03T01:02:00Z", {
                "window_id": window_id, "source_id": "check-b", "outcome": "OBSERVED",
            }),
            make_event("run-1", 1, "FINISHED", "2026-11-03T01:10:00Z", {
                "run_status": "OK", "sources_expected": ["check-a", "check-b"],
                "sources_failed": [], "collected_records": 1,
                "product_price_snapshots": 1, "retail_offer_batches": 0,
                "started_at": scheduled_at, "completed_at": "2026-11-03T01:10:00Z",
            }),
        ]
        manual = make_event("manual-run", 1, "STARTED", "2026-11-03T01:20:00Z", {
            "trigger": "workflow_dispatch", "scheduled_at": None,
        })
        result = build_continuity_report(CADENCE, PLAN, AS_OF, linked + [manual])
        observed = next(item for item in result["windows"] if item["window_id"] == window_id)
        self.assertEqual(observed["status"], "OBSERVED")
        self.assertEqual(result["window_counts"]["OBSERVED"], 1)
        self.assertGreater(result["window_counts"]["UNKNOWN"], 0)
        self.assertIsNone(result["observation_coverage_ratio"])

    def test_future_windows_are_not_counted_by_pipeline(self):
        result = build_continuity_report(CADENCE, PLAN, "2026-11-03T01:30:00Z", [])
        self.assertTrue(all(
            datetime.fromisoformat(row["scheduled_at"].replace("Z", "+00:00"))
            <= datetime.fromisoformat(result["as_of"].replace("Z", "+00:00"))
            for row in result["windows"]
        ))

    def test_no_enabled_sources_stays_unknown(self):
        empty = {
            "expected_sources": [],
            "not_scheduled_sources": ["disabled-c"],
            "providers": {"disabled-c": "reddit"},
        }
        result = build_continuity_report(CADENCE, empty, AS_OF, [])
        self.assertEqual(result["continuity_status"], "UNKNOWN")
        self.assertEqual(result["unknown_reason"], "NO_ENABLED_SOURCES")

    def test_invalid_journal_is_rejected_before_report(self):
        invalid = make_event("broken", 1, "FINISHED", "2026-11-03T01:00:00Z", {
            "run_status": "OK",
        })
        with self.assertRaises(ValueError):
            build_continuity_report(CADENCE, PLAN, AS_OF, [invalid])


if __name__ == "__main__":
    unittest.main()
