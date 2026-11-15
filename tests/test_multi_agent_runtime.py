"""Tests du moteur d'exécution multi-agents EDGE, 100% locaux."""
import unittest
import threading
import time

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
        mock_result = next(x for x in c["task_results"] if x["agent_id"] == "market_intelligence")
        self.assertEqual(mock_result["mode"], "mock")
        self.assertEqual(mock_result["status"], "simulated")

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
        rejected = next(x for x in c["task_results"] if x["agent_id"] == "market_intelligence")
        self.assertEqual(rejected["status"], "rejected")
        self.assertEqual(c["facts"], [])

    def test_fact_without_source_and_extract_or_dataset_is_rejected(self):
        p = plan()
        task = {"task_id": "sq-market::market_intelligence", "agent_id": "market_intelligence",
                "evidence_refs": p["tasks"][0]["evidence_refs"]}
        out = self.result(task)
        out["findings"][0]["evidence_refs"] = {"extract_ids": [], "dataset_ids": [], "source_ids": ["src-1"]}
        with self.assertRaises(SpecialistResultRejected):
            validate_specialist_result(out, task)

    def test_failed_or_no_data_task_cannot_return_findings(self):
        p = plan()
        task = {"task_id": "sq-market::market_intelligence", "agent_id": "market_intelligence",
                "evidence_refs": p["tasks"][0]["evidence_refs"]}
        for status in ("failed", "no_data"):
            with self.subTest(status=status):
                with self.assertRaises(SpecialistResultRejected):
                    validate_specialist_result(self.result(task, status=status), task)

    def test_mock_cannot_claim_real_or_return_findings(self):
        p = plan()
        task = {"task_id": "sq-market::market_intelligence", "agent_id": "market_intelligence",
                "evidence_refs": p["tasks"][0]["evidence_refs"]}
        out = self.result(task, mode="mock", status="simulated")
        with self.assertRaises(SpecialistResultRejected):
            validate_specialist_result(out, task)

    def test_parallel_execution_respects_worker_limit(self):
        lock = threading.Lock()
        active = {"count": 0, "maximum": 0}

        class Concurrent(StaticAdapter):
            def execute(self, task, context):
                with lock:
                    active["count"] += 1
                    active["maximum"] = max(active["maximum"], active["count"])
                time.sleep(0.04)
                with lock:
                    active["count"] -= 1
                return RuntimeTests().result(task)

        p = plan()
        p["tasks"][0]["assigned_roles"] = ["a", "b"]
        result = TaskExecutor({"a": Concurrent(None), "b": Concurrent(None)},
                              max_workers=2, task_timeout_seconds=1).execute(p)
        self.assertEqual([x["status"] for x in result["tasks"]], ["completed", "completed"])
        self.assertEqual(active["maximum"], 2)
        self.assertEqual(result["max_workers"], 2)

    def test_slow_adapter_is_marked_timed_out(self):
        class Slow(StaticAdapter):
            def execute(self, task, context):
                time.sleep(0.12)
                return RuntimeTests().result(task)

        result = TaskExecutor({"market_intelligence": Slow(None)},
                              task_timeout_seconds=0.02).execute(plan())
        task = next(x for x in result["tasks"] if x["agent_id"] == "market_intelligence")
        self.assertEqual(task["status"], "timed_out")
        self.assertIn("coopératif", " ".join(task["limitations"]))

    def test_retry_only_occurs_for_explicit_retryable_exception(self):
        class TemporaryError(Exception):
            retryable = True

        class Flaky(StaticAdapter):
            def __init__(self):
                self.calls = 0
            def execute(self, task, context):
                self.calls += 1
                if self.calls == 1:
                    raise TemporaryError()
                return RuntimeTests().result(task)

        adapter = Flaky()
        result = TaskExecutor({"market_intelligence": adapter}, max_retries=1).execute(plan())
        self.assertEqual(adapter.calls, 2)
        audit = next(x for x in result["audit"] if x["task_id"].endswith("market_intelligence"))
        self.assertEqual(audit["attempts"], 2)

    def test_non_retryable_exception_is_not_retried(self):
        class Broken(StaticAdapter):
            def __init__(self):
                self.calls = 0
            def execute(self, task, context):
                self.calls += 1
                raise RuntimeError("permanent")

        adapter = Broken()
        result = TaskExecutor({"market_intelligence": adapter}, max_retries=2).execute(plan())
        self.assertEqual(adapter.calls, 1)
        task = next(x for x in result["tasks"] if x["agent_id"] == "market_intelligence")
        self.assertEqual(task["status"], "failed")

    def test_total_specialist_task_count_is_bounded(self):
        p = {"scope": "tcg", "tasks": [
            {"subquestion_id": f"sq-{i}", "assigned_roles": ["a", "b"],
             "evidence_refs": {"extract_ids": [], "dataset_ids": [], "source_ids": []}}
            for i in range(3)
        ]}
        with self.assertRaises(ValueError):
            TaskExecutor(max_tasks=5).execute(p)

    def test_invalid_evidence_is_rejected_before_adapter_invocation(self):
        class MustNotRun(StaticAdapter):
            def execute(self, task, context):
                raise AssertionError("adapter must not be called")
        p = plan()
        p["tasks"][0]["evidence_refs"]["source_ids"] = "not-a-list"
        with self.assertRaises(SpecialistResultRejected):
            TaskExecutor({"market_intelligence": MustNotRun(None)}).execute(p)

    def test_duplicate_specialist_task_ids_are_rejected(self):
        p = plan()
        p["tasks"].append(dict(p["tasks"][0]))
        with self.assertRaises(ValueError):
            TaskExecutor().execute(p)

    def test_executor_limits_are_validated(self):
        for kwargs in ({"max_workers": 0}, {"max_workers": 17},
                       {"task_timeout_seconds": 0}, {"max_retries": 3}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    TaskExecutor(**kwargs)

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
