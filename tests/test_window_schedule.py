import unittest
from datetime import datetime, timezone

from intelligence.window_schedule import build_expected_windows


PLAN = {
    "expected_sources": ["lego_ebay", "pokemon_cardmarket"],
    "not_scheduled_sources": ["reddit_disabled"],
    "providers": {
        "lego_ebay": "ebay",
        "pokemon_cardmarket": "cardmarket",
        "reddit_disabled": "reddit",
    },
}


def cadence(**overrides):
    value = {
        "schedule_id": "mri-hourly",
        "timezone": "Europe/Paris",
        "interval_minutes": 60,
        "lookback_days": 0,
    }
    value.update(overrides)
    return value


class WindowScheduleTests(unittest.TestCase):
    def test_missing_cadence_preserves_unknown_and_does_not_invent_windows(self):
        result = build_expected_windows(None, PLAN, "2026-11-03T12:00:00Z")
        self.assertEqual(result["schedule_status"], "UNKNOWN")
        self.assertEqual(result["schedule_reason"], "CADENCE_NOT_CONFIGURED")
        self.assertEqual(result["expected_windows"], [])
        self.assertEqual(result["not_scheduled_sources"], ["reddit_disabled"])

    def test_as_of_must_be_timezone_aware(self):
        with self.assertRaises(ValueError):
            build_expected_windows(cadence(), PLAN, "2026-11-03T12:00:00")

    def test_as_of_accepts_aware_datetime(self):
        result = build_expected_windows(
            cadence(), PLAN, datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
        )
        self.assertEqual(result["as_of"], "2026-11-03T12:00:00Z")

    def test_timezone_equivalent_as_of_values_produce_same_windows(self):
        utc = build_expected_windows(cadence(), PLAN, "2026-11-03T12:00:00Z")
        paris = build_expected_windows(cadence(), PLAN, "2026-11-03T13:00:00+01:00")
        self.assertEqual(utc["expected_windows"], paris["expected_windows"])

    def test_window_ids_are_deterministic(self):
        first = build_expected_windows(cadence(), PLAN, "2026-11-03T12:00:00Z")
        second = build_expected_windows(cadence(), PLAN, "2026-11-03T12:00:00Z")
        self.assertEqual(
            [row["window_id"] for row in first["expected_windows"]],
            [row["window_id"] for row in second["expected_windows"]],
        )

    def test_as_of_boundary_is_inclusive(self):
        result = build_expected_windows(cadence(), PLAN, "2026-11-03T12:00:00+01:00")
        self.assertIn(
            "mri-hourly:20261103T110000Z",
            [row["window_id"] for row in result["expected_windows"]],
        )

    def test_future_windows_are_never_included(self):
        result = build_expected_windows(cadence(), PLAN, "2026-11-03T11:30:00Z")
        self.assertNotIn(
            "mri-hourly:20261103T120000Z",
            [row["window_id"] for row in result["expected_windows"]],
        )
        self.assertTrue(all(
            row["scheduled_at"] <= result["as_of"]
            for row in result["expected_windows"]
        ))

    def test_lookback_is_measured_in_local_calendar_days(self):
        result = build_expected_windows(
            cadence(lookback_days=1), PLAN, "2026-11-03T12:00:00Z"
        )
        from zoneinfo import ZoneInfo
        dates = {
            datetime.fromisoformat(row["scheduled_at"].replace("Z", "+00:00"))
            .astimezone(ZoneInfo("Europe/Paris")).date().isoformat()
            for row in result["expected_windows"]
        }
        self.assertEqual(dates, {"2026-11-02", "2026-11-03"})

    def test_spring_forward_skips_nonexistent_local_hour(self):
        result = build_expected_windows(
            cadence(lookback_days=0),
            PLAN,
            "2026-03-29T03:00:00+02:00",
        )
        instants = [row["scheduled_at"] for row in result["expected_windows"]]
        self.assertIn("2026-03-29T00:00:00Z", instants)  # 01:00 CET
        self.assertIn("2026-03-29T01:00:00Z", instants)  # 03:00 CEST
        self.assertEqual(
            instants,
            ["2026-03-28T23:00:00Z", "2026-03-29T00:00:00Z",
             "2026-03-29T01:00:00Z"],
        )

    def test_fall_back_retains_both_occurrences_of_ambiguous_hour(self):
        result = build_expected_windows(
            cadence(lookback_days=0),
            PLAN,
            "2026-10-25T03:00:00+01:00",
        )
        instants = [row["scheduled_at"] for row in result["expected_windows"]]
        self.assertIn("2026-10-25T00:00:00Z", instants)  # 02:00 CEST, fold 0
        self.assertIn("2026-10-25T01:00:00Z", instants)  # 02:00 CET, fold 1
        self.assertEqual(len(instants), len(set(instants)))

    def test_disabled_sources_never_enter_expected_source_ids(self):
        result = build_expected_windows(cadence(), PLAN, "2026-11-03T12:00:00Z")
        for row in result["expected_windows"]:
            self.assertEqual(row["expected_sources"], ["lego_ebay", "pokemon_cardmarket"])
            self.assertNotIn("reddit_disabled", row["expected_sources"])
        self.assertEqual(result["not_scheduled_sources"], ["reddit_disabled"])

    def test_check_ids_can_map_to_provider_source_ids(self):
        result = build_expected_windows(
            cadence(), PLAN, "2026-11-03T12:00:00Z",
            {"lego_ebay": "ebay:lego", "pokemon_cardmarket": "cardmarket:pokemon"},
        )
        self.assertEqual(
            result["expected_windows"][0]["expected_sources"],
            ["cardmarket:pokemon", "ebay:lego"],
        )
        self.assertEqual(result["source_mapping"]["lego_ebay"], "ebay:lego")

    def test_duplicate_mapped_source_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            build_expected_windows(
                cadence(), PLAN, "2026-11-03T12:00:00Z",
                {"lego_ebay": "same", "pokemon_cardmarket": "same"},
            )

    def test_disabled_source_cannot_be_mapped(self):
        with self.assertRaises(ValueError):
            build_expected_windows(
                cadence(), PLAN, "2026-11-03T12:00:00Z",
                {"reddit_disabled": "reddit:disabled"},
            )

    def test_no_enabled_sources_keeps_schedule_unknown(self):
        plan = {
            "expected_sources": [],
            "not_scheduled_sources": ["reddit_disabled"],
            "providers": {"reddit_disabled": "reddit"},
        }
        result = build_expected_windows(cadence(), plan, "2026-11-03T12:00:00Z")
        self.assertEqual(result["schedule_status"], "UNKNOWN")
        self.assertEqual(result["schedule_reason"], "NO_ENABLED_SOURCES")
        self.assertEqual(result["expected_windows"], [])

    def test_invalid_timezone_is_rejected(self):
        with self.assertRaises(ValueError):
            build_expected_windows(cadence(timezone="Mars/Olympus"), PLAN, "2026-11-03T12:00:00Z")

    def test_interval_must_be_positive_divisor_of_day(self):
        for value in (0, -5, 7, 1441, True, 60.0):
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_expected_windows(cadence(interval_minutes=value), PLAN, "2026-11-03T12:00:00Z")

    def test_lookback_bounds_are_enforced(self):
        for value in (-1, 367, True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_expected_windows(cadence(lookback_days=value), PLAN, "2026-11-03T12:00:00Z")

    def test_schedule_configuration_must_be_explicit_and_complete(self):
        with self.assertRaises(ValueError):
            build_expected_windows(
                {"timezone": "Europe/Paris", "interval_minutes": 60, "lookback_days": 1},
                PLAN,
                "2026-11-03T12:00:00Z",
            )

    def test_source_plan_duplicate_ids_are_rejected(self):
        plan = {
            "expected_sources": ["same", "same"],
            "not_scheduled_sources": [],
            "providers": {"same": "ebay"},
        }
        with self.assertRaises(ValueError):
            build_expected_windows(cadence(), plan, "2026-11-03T12:00:00Z")

    def test_source_plan_enabled_and_disabled_overlap_is_rejected(self):
        plan = {
            "expected_sources": ["same"],
            "not_scheduled_sources": ["same"],
            "providers": {"same": "ebay"},
        }
        with self.assertRaises(ValueError):
            build_expected_windows(cadence(), plan, "2026-11-03T12:00:00Z")

    def test_provider_is_required_for_every_check_id(self):
        plan = {
            "expected_sources": ["missing-provider"],
            "not_scheduled_sources": [],
            "providers": {},
        }
        with self.assertRaises(ValueError):
            build_expected_windows(cadence(), plan, "2026-11-03T12:00:00Z")

    def test_schedule_id_is_part_of_stable_window_identity(self):
        first = build_expected_windows(cadence(), PLAN, "2026-11-03T12:00:00Z")
        second = build_expected_windows(
            cadence(schedule_id="mri-hourly-v2"), PLAN, "2026-11-03T12:00:00Z"
        )
        self.assertNotEqual(
            first["expected_windows"][0]["window_id"],
            second["expected_windows"][0]["window_id"],
        )


if __name__ == "__main__":
    unittest.main()
