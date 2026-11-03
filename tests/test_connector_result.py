import unittest

from connectors.result import (
    ConnectorResult, OBSERVED, NO_REACTION_OBSERVED, SOURCE_FAILED,
    NOT_SCHEDULED, UNKNOWN, completed_query, failed_query, not_scheduled,
    unknown,
)


class ConnectorResultTests(unittest.TestCase):
    def test_completed_query_with_evidence_is_observed(self):
        result = completed_query(3)
        self.assertEqual(result, ConnectorResult(OBSERVED, True, 3))

    def test_completed_empty_query_is_no_reaction(self):
        result = completed_query(0)
        self.assertEqual(result.status, NO_REACTION_OBSERVED)
        self.assertTrue(result.query_completed)

    def test_failed_query_records_only_exception_class(self):
        error = RuntimeError("private token and provider response")
        result = failed_query(error)
        self.assertEqual(result.status, SOURCE_FAILED)
        self.assertEqual(result.error_type, "RuntimeError")
        self.assertNotIn("private", repr(result))
        self.assertNotIn("provider response", repr(result))

    def test_not_scheduled_is_not_failure(self):
        result = not_scheduled()
        self.assertEqual(result.status, NOT_SCHEDULED)
        self.assertIsNone(result.error_type)

    def test_unknown_is_not_failure(self):
        self.assertEqual(unknown().status, UNKNOWN)

    def test_legacy_none_is_not_implicitly_classified(self):
        # There is intentionally no API that accepts a legacy return value
        # and silently treats None as a completed empty search.
        with self.assertRaises(TypeError):
            completed_query(None)

    def test_completed_query_rejects_negative_count(self):
        with self.assertRaises(ValueError):
            completed_query(-1)

    def test_completed_query_rejects_boolean_count(self):
        with self.assertRaises(ValueError):
            completed_query(True)

    def test_completed_query_rejects_float_count(self):
        with self.assertRaises(ValueError):
            completed_query(1.5)

    def test_observed_requires_evidence(self):
        with self.assertRaises(ValueError):
            ConnectorResult(OBSERVED, True, 0)

    def test_no_reaction_requires_completed_empty_query(self):
        with self.assertRaises(ValueError):
            ConnectorResult(NO_REACTION_OBSERVED, False, 0)

    def test_failed_requires_exception_class(self):
        with self.assertRaises(ValueError):
            ConnectorResult(SOURCE_FAILED, False)

    def test_failed_cannot_claim_completed_query(self):
        with self.assertRaises(ValueError):
            ConnectorResult(SOURCE_FAILED, True, None, "TimeoutError")

    def test_journal_payload_is_strict_and_sanitized(self):
        result = completed_query(2)
        self.assertEqual(
            result.to_event_payload("window-1", "ebay-watch-1"),
            {"window_id": "window-1", "source_id": "ebay-watch-1", "outcome": OBSERVED},
        )

    def test_error_details_never_enter_journal_payload(self):
        result = failed_query(ValueError("sensitive provider body"))
        self.assertEqual(
            result.to_event_payload("window-1", "reddit-watch-1"),
            {"window_id": "window-1", "source_id": "reddit-watch-1", "outcome": SOURCE_FAILED},
        )

    def test_non_execution_states_cannot_be_journal_source_results(self):
        for result in (not_scheduled(), unknown()):
            with self.subTest(status=result.status):
                with self.assertRaises(ValueError):
                    result.to_event_payload("window-1", "source-1")

    def test_journal_identity_must_be_non_empty(self):
        with self.assertRaises(ValueError):
            completed_query(0).to_event_payload("", "source-1")
        with self.assertRaises(ValueError):
            completed_query(0).to_event_payload("window-1", " ")

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValueError):
            ConnectorResult("EMPTY", False)

    def test_evidence_count_rejects_bool_and_negative(self):
        with self.assertRaises(ValueError):
            ConnectorResult(UNKNOWN, False, True)
        with self.assertRaises(ValueError):
            ConnectorResult(UNKNOWN, False, -1)


if __name__ == "__main__":
    unittest.main()
