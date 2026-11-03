import unittest
from datetime import datetime, timedelta

from intelligence.reconstruct_continuity import reconstruct_windows
from intelligence.remote_journal_simulator import InMemoryRemoteJournal, make_event


T0 = "2026-11-03T01:00:00Z"
T1 = "2026-11-03T01:01:00Z"
T2 = "2026-11-03T02:00:00Z"
T3 = "2026-11-03T02:01:00Z"


def run_events(run_id, scheduled_at, finished=True):
    events = [make_event(run_id, 1, "STARTED", scheduled_at, {
        "trigger": "schedule", "scheduled_at": scheduled_at,
    })]
    if finished:
        completed_at = (datetime.fromisoformat(scheduled_at.replace("Z", "+00:00")) + timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
        events.append(make_event(run_id, 1, "FINISHED", completed_at, {
            "run_status": "PARTIAL", "sources_expected": ["source-a"],
            "sources_failed": [], "collected_records": 0,
            "product_price_snapshots": 0, "retail_offer_batches": 0,
            "started_at": scheduled_at, "completed_at": completed_at,
        }))
    return events


class ReconstructContinuityTests(unittest.TestCase):
    def test_reconstructs_distinct_outcomes_and_missed_window_across_runs(self):
        events = run_events("run-a", T0) + run_events("run-b", T2)
        expected = [
            {"window_id": "w1", "scheduled_at": T0, "expected_sources": ["source-a"]},
            {"window_id": "w2", "scheduled_at": "2026-11-03T01:30:00Z", "expected_sources": ["source-a"]},
            {"window_id": "w3", "scheduled_at": T2, "expected_sources": ["source-a"]},
        ]
        outcomes = [
            {"window_id": "w1", "run_id": "run-a", "attempt": 1,
             "source_id": "source-a", "outcome": "NO_REACTION_OBSERVED", "occurred_at": T1},
            {"window_id": "w3", "run_id": "run-b", "attempt": 1,
             "source_id": "source-a", "outcome": "OBSERVED", "occurred_at": T3},
        ]
        result = reconstruct_windows(expected, events, outcomes, "2026-11-03T03:00:00Z")
        self.assertEqual(result["window_counts"]["NO_REACTION_OBSERVED"], 1)
        self.assertEqual(result["window_counts"]["OBSERVED"], 1)
        self.assertEqual(result["window_counts"]["MISSED"], 1)
        self.assertEqual(result["continuity_status"], "GAP")
        self.assertEqual(result["observation_coverage_ratio"], 2 / 3)
        self.assertEqual(result["attempt_coverage_ratio"], 2 / 3)

    def test_reconstructs_from_restored_journal_history(self):
        journal = InMemoryRemoteJournal()
        for event in run_events("run-a", T0) + run_events("run-b", T2):
            journal.append_if_head(journal.head, event)
        restored_events = journal.read_events()
        expected = [
            {"window_id": "w1", "scheduled_at": T0, "expected_sources": ["source-a"]},
            {"window_id": "w2", "scheduled_at": T2, "expected_sources": ["source-a"]},
        ]
        outcomes = [
            {"window_id": "w1", "run_id": "run-a", "attempt": 1,
             "source_id": "source-a", "outcome": "OBSERVED", "occurred_at": T1},
            {"window_id": "w2", "run_id": "run-b", "attempt": 1,
             "source_id": "source-a", "outcome": "NO_REACTION_OBSERVED", "occurred_at": T3},
        ]
        result = reconstruct_windows(expected, restored_events, outcomes,
                                      "2026-11-03T03:00:00Z")
        self.assertEqual(result["continuity_status"], "CONTINUOUS")
        self.assertEqual(result["observation_coverage_ratio"], 1.0)
        self.assertEqual(result["window_counts"]["OBSERVED"], 1)
        self.assertEqual(result["window_counts"]["NO_REACTION_OBSERVED"], 1)

    def test_source_failure_is_not_missed_or_no_reaction(self):
        events = run_events("run-a", T0)
        outcome = {"window_id": "w1", "run_id": "run-a", "attempt": 1,
                   "source_id": "source-a", "outcome": "SOURCE_FAILED", "occurred_at": T1}
        result = reconstruct_windows([{"window_id": "w1", "scheduled_at": T0, "expected_sources": ["source-a"]}],
                                      events, [outcome], T2)
        self.assertEqual(result["window_counts"]["SOURCE_FAILED"], 1)
        self.assertEqual(result["window_counts"]["MISSED"], 0)
        self.assertEqual(result["continuity_status"], "DEGRADED")
        self.assertEqual(result["observation_coverage_ratio"], 0.0)
        self.assertEqual(result["attempt_coverage_ratio"], 1.0)

    def test_started_run_without_finish_or_evidence_is_unknown_not_missed(self):
        events = run_events("run-a", T0, finished=False)
        result = reconstruct_windows([{"window_id": "w1", "scheduled_at": T0, "expected_sources": ["source-a"]}],
                                      events, [], T2)
        self.assertEqual(result["window_counts"]["UNKNOWN"], 1)
        self.assertEqual(result["window_counts"]["MISSED"], 0)
        self.assertIsNone(result["observation_coverage_ratio"])

    def test_finished_run_without_source_evidence_is_unknown_not_missed(self):
        events = run_events("run-a", T0, finished=True)
        result = reconstruct_windows([{"window_id": "w1", "scheduled_at": T0, "expected_sources": ["source-a"]}],
                                      events, [], T2)
        self.assertEqual(result["window_counts"]["UNKNOWN"], 1)
        self.assertEqual(result["window_counts"]["MISSED"], 0)
        self.assertIsNone(result["observation_coverage_ratio"])

    def test_multiple_sources_aggregate_observation_and_partial_failure(self):
        events = run_events("run-a", T0)
        expected = [{"window_id": "w1", "scheduled_at": T0,
                     "expected_sources": ["source-a", "source-b"]}]
        outcomes = [
            {"window_id": "w1", "run_id": "run-a", "attempt": 1,
             "source_id": "source-a", "outcome": "NO_REACTION_OBSERVED", "occurred_at": T1},
            {"window_id": "w1", "run_id": "run-a", "attempt": 1,
             "source_id": "source-b", "outcome": "SOURCE_FAILED", "occurred_at": T1},
        ]
        result = reconstruct_windows(expected, events, outcomes, T2)
        self.assertEqual(result["window_counts"]["DEGRADED"], 1)
        self.assertEqual(result["source_counts"]["SOURCE_FAILED"], 1)
        self.assertEqual(result["observation_coverage_ratio"], 0.5)
        self.assertEqual(result["attempt_coverage_ratio"], 1.0)
        self.assertEqual(result["continuity_status"], "DEGRADED")

    def test_missing_one_expected_source_makes_window_unknown(self):
        events = run_events("run-a", T0)
        expected = [{"window_id": "w1", "scheduled_at": T0,
                     "expected_sources": ["source-a", "source-b"]}]
        outcomes = [{
            "window_id": "w1", "run_id": "run-a", "attempt": 1,
            "source_id": "source-a", "outcome": "OBSERVED", "occurred_at": T1,
        }]
        result = reconstruct_windows(expected, events, outcomes, T2)
        self.assertEqual(result["window_counts"]["UNKNOWN"], 1)
        self.assertEqual(result["windows"][0]["missing_sources"], ["source-b"])
        self.assertIsNone(result["observation_coverage_ratio"])

    def test_source_not_expected_for_window_is_rejected(self):
        events = run_events("run-a", T0)
        outcome = {"window_id": "w1", "run_id": "run-a", "attempt": 1,
                   "source_id": "unexpected", "outcome": "OBSERVED", "occurred_at": T1}
        with self.assertRaises(ValueError):
            reconstruct_windows([{"window_id": "w1", "scheduled_at": T0,
                                  "expected_sources": ["source-a"]}],
                                events, [outcome], T2)

    def test_outcome_without_verified_started_run_is_rejected(self):
        outcome = {"window_id": "w1", "run_id": "missing", "attempt": 1,
                   "source_id": "source-a", "outcome": "OBSERVED", "occurred_at": T1}
        with self.assertRaises(ValueError):
            reconstruct_windows([{"window_id": "w1", "scheduled_at": T0, "expected_sources": ["source-a"]}], [],
                                [outcome], T2)

    def test_corrupt_run_history_is_rejected(self):
        invalid = make_event("run-a", 1, "FINISHED", T1, {"run_status": "OK"})
        with self.assertRaises(ValueError):
            reconstruct_windows([{"window_id": "w1", "scheduled_at": T0, "expected_sources": ["source-a"]}],
                                [invalid], [], T2)

    def test_future_expected_window_is_not_counted(self):
        future = {"window_id": "future", "scheduled_at": T3, "expected_sources": ["source-a"]}
        result = reconstruct_windows([future], [], [], T2)
        self.assertEqual(result["expected_windows"], 0)
        self.assertIsNone(result["observation_coverage_ratio"])

    def test_duplicate_window_outcomes_are_rejected(self):
        events = run_events("run-a", T0)
        outcome = {"window_id": "w1", "run_id": "run-a", "attempt": 1,
                   "source_id": "source-a", "outcome": "OBSERVED", "occurred_at": T1}
        with self.assertRaises(ValueError):
            reconstruct_windows([{"window_id": "w1", "scheduled_at": T0, "expected_sources": ["source-a"]}],
                                events, [outcome, outcome], T2)


if __name__ == "__main__":
    unittest.main()
