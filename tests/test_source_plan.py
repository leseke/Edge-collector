import unittest

from intelligence.source_plan import build_source_plan


class SourcePlanTests(unittest.TestCase):
    def test_plan_uses_stable_check_ids_and_separates_disabled_sources(self):
        plan = build_source_plan(
            {"enabled_sources": {"ebay": False, "reddit": True}},
            [{"id": "lego_77073", "source": "ebay"},
             {"id": "lorcana_box", "source": "cardmarket"}],
            [{"id": "trends_lego", "keyword": "LEGO"}],
            [{"id": "reddit_lego", "query": "LEGO"}],
            [{"id": "scavio_lego", "query": "LEGO"}],
        )
        self.assertEqual(
            plan["expected_sources"],
            ["lorcana_box", "trends_lego", "reddit_lego", "scavio_lego"],
        )
        self.assertEqual(plan["not_scheduled_sources"], ["lego_77073"])
        self.assertEqual(plan["providers"]["lego_77073"], "ebay")
        self.assertEqual(plan["providers"]["lorcana_box"], "cardmarket")

    def test_duplicate_check_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            build_source_plan(
                {},
                [{"id": "same", "source": "ebay"}],
                [{"id": "same", "keyword": "LEGO"}],
                [],
                [],
            )

    def test_missing_check_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            build_source_plan({}, [{"id": "", "source": "ebay"}], [], [], [])

    def test_all_disabled_sources_produce_no_expected_checks(self):
        plan = build_source_plan(
            {"enabled_sources": {"ebay": False, "trends": False}},
            [{"id": "lego_77073", "source": "ebay"}],
            [{"id": "trends_lego", "keyword": "LEGO"}],
            [],
            [],
        )
        self.assertEqual(plan["expected_sources"], [])
        self.assertEqual(plan["not_scheduled_sources"], ["lego_77073", "trends_lego"])


if __name__ == "__main__":
    unittest.main()
