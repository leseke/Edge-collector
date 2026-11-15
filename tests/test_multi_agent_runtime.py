"""Tests du moteur d'exécution multi-agents EDGE, 100% locaux."""
import unittest

from intelligence.multi_agent_runtime import (
    CONTRACT, Coordinator, MockSpecialistAdapter, SpecialistAdapter,
    SpecialistResultRejected, TaskExecutor, validate_specialist_result,
)


def plan():
    return {"scope": "tcg", "tasks": [{
        "subquestion_id": "sq-market", "topic_id": "market",
        "assigned_roles": ["market_intelligence", "supply_distribution"],
        "evidence_refs": {"extract_ids": ["ext-1"], "dataset_ids": ["ds-1"], "source_ids": ["src-1"]},
    }]}


def finding(kind="FACT", position="positive"):
    return {
        "finding_id": "f-1", "classification": kind, "statement": "Observation issue des éléments référencés.",
        "evidence_refs": {"extract_ids": ["ext-1"], "dataset_ids": [], "source_ids": ["src-1"]},
        "confidence": "medium", "assertion_key": "market-direction", "position": position,
    }


class StaticAdapter(SpecialistAdapter):
    def __init__(self, output, paid=False):
        self.output, self.paid = output, paid

    def execute(self, task, context):
        return self.output(task) if callable(self.output) else self.output


class RuntimeTests(unittest.TestCase):
    def result(self, task, **overrides):
        out = {"contract": CONTRACT, "task_id": task["task_id"], "agent_id": task["agent_id"],
               "mode": "real", "status": "completed", "findings": [finding()], "limitations": []}
        out.update(overrides)
        return out

    def test_mock_is_explicit_and_never_creates_findings(self):
        c = Coordinator(TaskExecutor({"market_intelligence": MockSpecialistAdapter()})).run(plan())
        self.assertEqual(c["execution"], "local_offline")
        self.assertEqual(c["paid_calls"], 0)
        self.assertEqual(c["facts"], [])
        self.assertEqual(c["task_results"][0]["mode"], "mock")
        self.assertEqual(c["task_results"][0]["status"], "simulated")

    def test_unconfigured_specialists_are_not_faked(self):
        c = Coordinator().run(plan())
        self.assertEqual([x["status"] for x in c["task_results"]], ["not_configured", "not_configured"])
        self.assertEqual(c["facts"], [])

    def test_paid_adapter_is_blocked_before_execution(self):
        class Paid(StaticAdapter):
            def execute(self, task, context):
                raise AssertionError("must never be invoked")
        c = Coordinator(TaskExecutor({"market_intelligence": Paid({}, paid=True)})).run(plan())
        self.assertEqual(c["task_results"][0]["status"], "blocked")
        self.assertEqual(c["paid_calls"], 0)

    def test_valid_fact_is_kept_unverified(self):
        adapter = StaticAdapter(lambda task: self.result(task))
        c = Coordinator(TaskExecutor({"market_intelligence": adapter})).run(plan())
        self.assertEqual(len(c["facts"]), 1)
        self.assertEqual(c["facts"][0]["verification"], "unverified")

    def test_unknown_evidence_rejects_whole_specialist_result(self):
        def forged(task):
            out = self.result(task)
            out["findings"][0]["evidence_refs"]["source_ids"] = ["src-invented"]
            return out
        c = Coordinator(TaskExecutor({"market_intelligence": StaticAdapter(forged)})).run(plan())
        self.assertEqual(c["task_results"][0]["status"], "rejected")
        self.assertEqual(c["facts"], [])

    def test_fact_without_source_and_extract_or_dataset_is_rejected(self):
        p = plan()
        task = {"task_id": "sq-market::market_intelligence", "agent_id": "market_intelligence",
                "evidence_refs": p["tasks"][0]["evidence_refs"]}
        out = self.result(task)
        out["findings"][0]["evidence_refs"] = {"extract_ids": [], "dataset_ids": [], "source_ids": ["src-1"]}
        with self.assertRaises(SpecialistResultRejected):
            validate_specialist_result(out, task)

    def test_mock_cannot_claim_real_or_return_findings(self):
        p = plan()
        task = {"task_id": "sq-market::market_intelligence", "agent_id": "market_intelligence",
                "evidence_refs": p["tasks"][0]["evidence_refs"]}
        out = self.result(task, mode="mock", status="simulated")
        with self.assertRaises(SpecialistResultRejected):
            validate_specialist_result(out, task)

    def test_contradictions_are_preserved_not_arbitrarily_resolved(self):
        def opposite(task):
            out = self.result(task)
            out["findings"][0]["position"] = "negative"
            return out
        adapters = {"market_intelligence": StaticAdapter(lambda task: self.result(task)),
                    "supply_distribution": StaticAdapter(opposite)}
        c = Coordinator(TaskExecutor(adapters)).run(plan())
        self.assertEqual(len(c["contradictions"]), 1)
        self.assertEqual(set(c["contradictions"][0]["positions"]), {"positive", "negative"})
        self.assertEqual(c["verification"], "unverified")


if __name__ == "__main__":
    unittest.main()
