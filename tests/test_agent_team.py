"""Tests du registre multi-agents EDGE. Aucun reseau, aucun fournisseur."""
import unittest

from intelligence.agent_team import (
    TCGScopeError, is_tcg_subject, route_topics,
)


class AgentTeamTests(unittest.TestCase):
    def test_tcg_and_directly_related_objects_are_in_scope(self):
        self.assertTrue(is_tcg_subject({"category": "tcg", "title": "Pokemon"}))
        self.assertTrue(is_tcg_subject({"category": "collectible", "tcg_link": True}))
        self.assertTrue(is_tcg_subject({"category": "accessory", "related_tcg": "Pokemon"}))

    def test_independent_collectibles_are_out_of_scope(self):
        self.assertFalse(is_tcg_subject({"category": "lego", "title": "LEGO set"}))
        self.assertFalse(is_tcg_subject({"category": "collectible", "title": "Funko Pop"}))
        with self.assertRaises(TCGScopeError):
            route_topics({"category": "lego"}, ["prix", "disponibilite"])

    def test_router_selects_only_relevant_specialists(self):
        result = route_topics(
            {"category": "tcg", "title": "Carte Pokemon"},
            [{"topic_id": "grading", "question": "PSA population and turnaround"},
             {"topic_id": "realized_prices", "question": "prix et ventes conclues"}],
        )
        self.assertEqual(result["execution"], "not_started")
        self.assertEqual(result["paid_calls"], 0)
        self.assertIn("coordinator", result["agent_ids"])
        self.assertIn("grading_intelligence", result["agent_ids"])
        self.assertIn("market_intelligence", result["agent_ids"])
        self.assertIn("opportunity_detection", result["agent_ids"])
        self.assertNotIn("restoration_preservation", result["agent_ids"])

    def test_build_team_plan_assigns_roles_per_subquestion_without_execution(self):
        from intelligence.agent_team import build_team_plan
        plan = build_team_plan(
            {"category": "tcg", "title": "Carte Pokemon"},
            [{"subquestion_id": "sq1", "topic_id": "grading",
              "question": "PSA population and turnaround"},
             {"subquestion_id": "sq2", "topic_id": "realized_prices",
              "question": "prix et ventes conclues"}],
        )
        self.assertEqual(plan["execution"], "planned_only")
        self.assertEqual(plan["paid_calls"], 0)
        self.assertEqual([t["subquestion_id"] for t in plan["tasks"]], ["sq1", "sq2"])
        self.assertIn("grading_intelligence", plan["tasks"][0]["assigned_roles"])
        self.assertIn("market_intelligence", plan["tasks"][1]["assigned_roles"])

    def test_router_can_skip_synthesis(self):
        result = route_topics({"category": "tcg"}, ["disponibilite"], include_synthesis=False)
        self.assertNotIn("opportunity_detection", result["agent_ids"])
        self.assertIn("supply_distribution", result["agent_ids"])


if __name__ == "__main__":
    unittest.main()
