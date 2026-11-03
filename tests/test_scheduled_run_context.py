import unittest

from connectors.result import completed_query, failed_query, unknown
from intelligence.remote_journal_simulator import make_event
from intelligence.scheduled_run_context import resolve_scheduled_run_context


SCHEDULED = "2026-11-03T01:00:00Z"
WINDOW = {
    "window_id": "hourly:20261103T010000Z",
    "scheduled_at": SCHEDULED,
    "expected_sources": ["ebay:item-a", "reddit:topic-a"],
}


def started(run_id, scheduled_at=SCHEDULED, attempt=1):
    return make_event(run_id, attempt, "STARTED", "2026-11-03T01:00:03Z", {
        "trigger": "schedule",
        "scheduled_at": scheduled_at,
    })


class ScheduledRunContextTests(unittest.TestCase):
    def test_resolves_only_explicit_window_and_matching_scheduled_instant(self):
        context = resolve_scheduled_run_context(
            [WINDOW], [started("run-a")], "run-a", 1, WINDOW["window_id"]
        )
        self.assertEqual(context.window_id, WINDOW["window_id"])
        self.assertEqual(context.scheduled_at, SCHEDULED)
        self.assertEqual(context.run_id, "run-a")
        self.assertEqual(context.attempt, 1)
        self.assertEqual(context.expected_sources, ("ebay:item-a", "reddit:topic-a"))

    def test_equivalent_timezone_offset_is_normalized_to_same_instant(self):
        event = started("run-a", "2026-11-03T02:00:00+01:00")
        context = resolve_scheduled_run_context(
            [WINDOW], [event], "run-a", 1, WINDOW["window_id"]
        )
        self.assertEqual(context.scheduled_at, SCHEDULED)

    def test_unknown_or_implicit_window_id_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_scheduled_run_context([WINDOW], [started("run-a")],
                                          "run-a", 1, "guessed-from-time")
        with self.assertRaises(ValueError):
            resolve_scheduled_run_context([WINDOW], [started("run-a")],
                                          "run-a", 1, None)

    def test_started_without_scheduled_at_is_not_associated_by_start_time(self):
        event = make_event("manual", 1, "STARTED", "2026-11-03T01:00:03Z", {
            "trigger": "workflow_dispatch", "scheduled_at": None,
        })
        with self.assertRaisesRegex(ValueError, "explicit scheduled_at"):
            resolve_scheduled_run_context([WINDOW], [event], "manual", 1,
                                          WINDOW["window_id"])

    def test_mismatched_scheduled_at_is_rejected(self):
        event = started("run-a", "2026-11-03T02:00:00Z")
        with self.assertRaisesRegex(ValueError, "does not match"):
            resolve_scheduled_run_context([WINDOW], [event], "run-a", 1,
                                          WINDOW["window_id"])

    def test_two_run_attempts_cannot_claim_one_window(self):
        events = [started("run-a"), started("run-b")]
        with self.assertRaisesRegex(ValueError, "zero or multiple"):
            resolve_scheduled_run_context([WINDOW], events, "run-a", 1,
                                          WINDOW["window_id"])

    def test_missing_or_invalid_run_attempt_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "no verified STARTED"):
            resolve_scheduled_run_context([WINDOW], [], "missing", 1,
                                          WINDOW["window_id"])
        with self.assertRaises(ValueError):
            resolve_scheduled_run_context([WINDOW], [started("run-a")],
                                          "run-a", True, WINDOW["window_id"])

    def test_duplicate_or_malformed_expected_window_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "exactly one"):
            resolve_scheduled_run_context([WINDOW, WINDOW], [started("run-a")],
                                          "run-a", 1, WINDOW["window_id"])
        malformed = {**WINDOW, "expected_sources": ["same", "same"]}
        with self.assertRaisesRegex(ValueError, "expected_sources"):
            resolve_scheduled_run_context([malformed], [started("run-a")],
                                          "run-a", 1, WINDOW["window_id"])

    def test_source_result_payload_is_limited_to_expected_source_and_allowlist(self):
        context = resolve_scheduled_run_context(
            [WINDOW], [started("run-a")], "run-a", 1, WINDOW["window_id"]
        )
        payload = context.source_result_payload(completed_query(2), "ebay:item-a")
        self.assertEqual(payload, {
            "window_id": WINDOW["window_id"],
            "source_id": "ebay:item-a",
            "outcome": "OBSERVED",
        })
        with self.assertRaisesRegex(ValueError, "not expected"):
            context.source_result_payload(completed_query(0), "unexpected")

    def test_unknown_result_cannot_be_written_as_source_result(self):
        context = resolve_scheduled_run_context(
            [WINDOW], [started("run-a")], "run-a", 1, WINDOW["window_id"]
        )
        with self.assertRaises(ValueError):
            context.source_result_payload(unknown(), "ebay:item-a")

    def test_failed_connector_result_keeps_only_safe_error_class(self):
        context = resolve_scheduled_run_context(
            [WINDOW], [started("run-a")], "run-a", 1, WINDOW["window_id"]
        )
        payload = context.source_result_payload(failed_query(RuntimeError("private detail")),
                                                "reddit:topic-a")
        self.assertEqual(payload["outcome"], "SOURCE_FAILED")
        self.assertEqual(set(payload), {"window_id", "source_id", "outcome"})
        self.assertNotIn("private detail", repr(payload))


if __name__ == "__main__":
    unittest.main()
