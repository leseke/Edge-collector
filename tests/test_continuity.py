import unittest
from intelligence.continuity import assess_continuity


class ContinuityTests(unittest.TestCase):
    def test_full_coverage(self):
        result = assess_continuity(
            ["2026-11-03T01:00:00Z", "2026-11-03T02:00:00Z"],
            [
                {"id": "a", "observed_at": "2026-11-03T01:01:00Z", "usable_market_observation": True},
                {"id": "b", "observed_at": "2026-11-03T02:02:00Z", "usable_market_observation": True},
            ],
            "2026-11-03T02:10:00Z",
            tolerance_minutes=5,
        )
        self.assertEqual(result["continuity_status"], "CONTINUOUS")
        self.assertEqual(result["coverage_ratio"], 1.0)

    def test_heartbeat_does_not_fill_market_window(self):
        result = assess_continuity(
            ["2026-11-03T01:00:00Z"],
            [{"id": "run", "observed_at": "2026-11-03T01:00:00Z", "usable_market_observation": False}],
            "2026-11-03T01:05:00Z",
        )
        self.assertEqual(result["missed_windows"], 1)
        self.assertEqual(result["continuity_status"], "GAP")

    def test_one_observation_cannot_fill_two_windows(self):
        result = assess_continuity(
            ["2026-11-03T01:00:00Z", "2026-11-03T01:05:00Z"],
            [{"id": "a", "observed_at": "2026-11-03T01:02:00Z", "usable_market_observation": True}],
            "2026-11-03T01:06:00Z",
            tolerance_minutes=5,
        )
        self.assertEqual(result["observed_windows"], 1)
        self.assertEqual(result["missed_windows"], 1)

    def test_future_observation_is_excluded(self):
        result = assess_continuity(
            ["2026-11-03T01:00:00Z"],
            [{"id": "a", "observed_at": "2026-11-03T01:10:00Z", "usable_market_observation": True}],
            "2026-11-03T01:05:00Z",
            tolerance_minutes=10,
        )
        self.assertEqual(result["observed_windows"], 0)

    def test_no_expected_windows_is_unknown_not_cash(self):
        result = assess_continuity([], [], "2026-11-03T01:05:00Z")
        self.assertEqual(result["continuity_status"], "UNKNOWN")
        self.assertIsNone(result["coverage_ratio"])

    def test_duplicate_observation_id_rejected(self):
        item = {"id": "same", "observed_at": "2026-11-03T01:00:00Z", "usable_market_observation": True}
        with self.assertRaises(ValueError):
            assess_continuity(["2026-11-03T01:00:00Z"], [item, item], "2026-11-03T01:05:00Z")

    def test_timezone_is_required(self):
        with self.assertRaises(ValueError):
            assess_continuity(["2026-11-03T01:00:00"], [], "2026-11-03T01:05:00Z")


if __name__ == "__main__":
    unittest.main()
