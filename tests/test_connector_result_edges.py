import unittest

from connectors.result import (
    ConnectorResult, SOURCE_FAILED, completed_query, failed_query,
)


class ConnectorResultEdgeTests(unittest.TestCase):
    def test_exception_message_is_not_retained(self):
        result = failed_query(RuntimeError("sensitive query and token"))
        self.assertEqual(result.error_type, "RuntimeError")
        self.assertNotIn("sensitive", repr(result))

    def test_error_type_must_be_single_line(self):
        with self.assertRaises(ValueError):
            ConnectorResult(SOURCE_FAILED, False, None, "RuntimeError\nsecret")

    def test_completed_zero_is_distinct_from_unknown(self):
        result = completed_query(0)
        self.assertEqual(result.status, "NO_REACTION_OBSERVED")
        self.assertTrue(result.query_completed)

    def test_positive_evidence_count_is_preserved_as_count_only(self):
        result = completed_query(7)
        self.assertEqual(result.evidence_count, 7)
        self.assertEqual(result.status, "OBSERVED")


if __name__ == "__main__":
    unittest.main()
