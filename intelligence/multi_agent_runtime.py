"""Offline-first execution engine for EDGE specialist tasks.

No provider is contacted by this module. Paid adapters are always refused here;
future paid execution must go through the existing R4.2 run_agent/SpendGuard path.
Mock output is explicitly marked simulated and is never promoted to evidence.
"""
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone

CONTRACT = "edge.specialist_result.v1"
CLASSIFICATIONS = {"FACT", "WEAK_SIGNAL", "INFERENCE", "BET"}
CONFIDENCE = {"low", "medium", "high"}
EVIDENCE_KEYS = ("extract_ids", "dataset_ids", "source_ids")
RESULT_KEYS = {"contract", "task_id", "agent_id", "mode", "status", "findings", "limitations"}
FINDING_KEYS = {"finding_id", "classification", "statement", "evidence_refs",
                "confidence", "assertion_key", "position"}


class SpecialistResultRejected(ValueError):
    pass


class SpecialistAdapter:
    """Interface for a future specialist; receives identifiers, not source text."""
    paid = False

    def execute(self, task, context):
        raise NotImplementedError


class MockSpecialistAdapter(SpecialistAdapter):
    """Explicit mock: exercises orchestration without inventing findings."""
    paid = False

    def execute(self, task, context):
        return {
            "contract": CONTRACT, "task_id": task["task_id"], "agent_id": task["agent_id"],
            "mode": "mock", "status": "simulated", "findings": [],
            "limitations": ["MOCK_ONLY: aucun spécialiste réel n'a été exécuté."],
        }


def _string_list(value, field):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        raise SpecialistResultRejected(f"{field}: liste d'identifiants invalide")
    if len(value) != len(set(value)):
        raise SpecialistResultRejected(f"{field}: identifiants dupliqués")
    return set(value)


def _task_evidence(task):
    refs = task.get("evidence_refs")
    if not isinstance(refs, dict) or set(refs) != set(EVIDENCE_KEYS):
        raise SpecialistResultRejected("tâche sans contrat evidence_refs complet")
    return {key: _string_list(refs[key], key) for key in EVIDENCE_KEYS}


def validate_specialist_result(result, task):
    """Validate shape, assignment and every evidence reference.

    FACT means source-grounded, not verified: verification remains unverified.
    """
    if not isinstance(result, dict) or set(result) != RESULT_KEYS:
        raise SpecialistResultRejected("contrat de résultat invalide")
    if result["contract"] != CONTRACT:
        raise SpecialistResultRejected("version de contrat inconnue")
    if result["task_id"] != task["task_id"] or result["agent_id"] != task["agent_id"]:
        raise SpecialistResultRejected("résultat rattaché à une autre tâche ou spécialité")
    if result["mode"] not in {"real", "mock"}:
        raise SpecialistResultRejected("mode d'exécution inconnu")
    if result["status"] not in {"completed", "no_data", "simulated", "failed"}:
        raise SpecialistResultRejected("statut de résultat inconnu")
    if not isinstance(result["limitations"], list) or any(not isinstance(x, str) for x in result["limitations"]):
        raise SpecialistResultRejected("limitations invalides")
    if not isinstance(result["findings"], list):
        raise SpecialistResultRejected("findings doit être une liste")
    if result["mode"] == "mock" and (result["status"] != "simulated" or result["findings"]):
        raise SpecialistResultRejected("un mock doit rester simulé et ne peut produire aucun finding")
    if result["mode"] == "real" and result["status"] == "simulated":
        raise SpecialistResultRejected("un résultat réel ne peut se déclarer simulé")

    allowed = _task_evidence(task)
    clean = []
    for finding in result["findings"]:
        if not isinstance(finding, dict) or set(finding) != FINDING_KEYS:
            raise SpecialistResultRejected("structure de finding invalide")
        if finding["classification"] not in CLASSIFICATIONS:
            raise SpecialistResultRejected("classification inconnue")
        if finding["confidence"] not in CONFIDENCE:
            raise SpecialistResultRejected("niveau de confiance inconnu")
        if not isinstance(finding["statement"], str) or not finding["statement"].strip():
            raise SpecialistResultRejected("énoncé vide")
        if finding["assertion_key"] is not None and not isinstance(finding["assertion_key"], str):
            raise SpecialistResultRejected("assertion_key invalide")
        if finding["position"] is not None and not isinstance(finding["position"], str):
            raise SpecialistResultRejected("position invalide")
        refs = finding["evidence_refs"]
        if not isinstance(refs, dict) or set(refs) != set(EVIDENCE_KEYS):
            raise SpecialistResultRejected("références de preuve incomplètes")
        normalized = {k: _string_list(refs[k], k) for k in EVIDENCE_KEYS}
        for key in EVIDENCE_KEYS:
            if not normalized[key] <= allowed[key]:
                raise SpecialistResultRejected(f"référence {key} absente du dossier partagé")
        if finding["classification"] == "FACT":
            if not normalized["source_ids"] or not (normalized["extract_ids"] or normalized["dataset_ids"]):
                raise SpecialistResultRejected("un FACT exige une source et un extrait ou dataset autorisé")
        clean.append({
            **deepcopy(finding),
            "evidence_refs": {k: sorted(normalized[k]) for k in EVIDENCE_KEYS},
            "verification": "unverified", "origin_mode": result["mode"],
        })
    return {**deepcopy(result), "findings": clean}


class TaskExecutor:
    """Runs only assigned, configured, free adapters; no implicit retries."""
    def __init__(self, adapters=None, max_tasks=100, max_specialists_per_task=9):
        self.adapters = dict(adapters or {})
        self.max_tasks = max_tasks
        self.max_specialists_per_task = max_specialists_per_task

    def execute(self, team_plan, context=None):
        if not isinstance(team_plan, dict) or team_plan.get("scope") != "tcg":
            raise ValueError("plan d'équipe TCG requis")
        tasks = team_plan.get("tasks")
        if not isinstance(tasks, list) or len(tasks) > self.max_tasks:
            raise ValueError("nombre de tâches invalide ou supérieur au plafond")
        context = deepcopy(context or {})
        outputs, audit = [], []
        for index, planned in enumerate(tasks):
            roles = planned.get("assigned_roles", [])
            if not isinstance(roles, list) or len(roles) > self.max_specialists_per_task:
                raise ValueError("nombre de spécialistes invalide ou supérieur au plafond")
            for role in roles:
                task_id = f"{planned.get('subquestion_id') or 'task-' + str(index + 1)}::{role}"
                task = {
                    "task_id": task_id, "agent_id": role,
                    "subquestion_id": planned.get("subquestion_id"), "topic_id": planned.get("topic_id"),
                    "evidence_refs": deepcopy(planned.get("evidence_refs", {})),
                }
                adapter = self.adapters.get(role)
                if adapter is None:
                    outputs.append({"task_id": task_id, "agent_id": role, "status": "not_configured",
                                    "mode": "none", "findings": [], "limitations": ["Aucun adaptateur configuré."]})
                    audit.append({"task_id": task_id, "event": "skipped", "reason": "adapter_unavailable"})
                    continue
                if getattr(adapter, "paid", False):
                    outputs.append({"task_id": task_id, "agent_id": role, "status": "blocked",
                                    "mode": "none", "findings": [], "limitations": ["Adaptateur payant bloqué hors SpendGuard."]})
                    audit.append({"task_id": task_id, "event": "blocked", "reason": "paid_adapter_requires_spendguard"})
                    continue
                started = datetime.now(timezone.utc).isoformat()
                try:
                    raw = adapter.execute(deepcopy(task), deepcopy(context))
                    validated = validate_specialist_result(raw, task)
                    outputs.append(validated)
                    audit.append({"task_id": task_id, "event": "completed", "started_at": started,
                                  "finished_at": datetime.now(timezone.utc).isoformat(),
                                  "mode": validated["mode"], "status": validated["status"]})
                except SpecialistResultRejected as exc:
                    outputs.append({"task_id": task_id, "agent_id": role, "status": "rejected",
                                    "mode": "none", "findings": [], "limitations": [str(exc)]})
                    audit.append({"task_id": task_id, "event": "rejected", "reason": str(exc)})
                except Exception as exc:
                    outputs.append({"task_id": task_id, "agent_id": role, "status": "failed",
                                    "mode": "none", "findings": [], "limitations": [type(exc).__name__]})
                    audit.append({"task_id": task_id, "event": "failed", "reason": type(exc).__name__})
        return {"contract": "edge.task_execution.v1", "execution": "local_offline",
                "paid_calls": 0, "tasks": outputs, "audit": audit}


class Coordinator:
    """Aggregates only validated findings and preserves unresolved conflicts."""
    def __init__(self, executor=None):
        self.executor = executor or TaskExecutor()

    def run(self, team_plan, context=None):
        execution = self.executor.execute(team_plan, context)
        buckets = {name: [] for name in ("FACT", "WEAK_SIGNAL", "INFERENCE", "BET")}
        for task in execution["tasks"]:
            for finding in task.get("findings", []):
                if finding.get("verification") == "unverified" and finding.get("classification") in buckets:
                    buckets[finding["classification"]].append({
                        **finding, "task_id": task["task_id"], "agent_id": task["agent_id"]
                    })
        positions = defaultdict(lambda: defaultdict(list))
        for finding in buckets["FACT"]:
            key, position = finding.get("assertion_key"), finding.get("position")
            if key and position:
                positions[key][position].append({
                    "task_id": finding["task_id"], "agent_id": finding["agent_id"],
                    "source_ids": finding["evidence_refs"]["source_ids"],
                })
        contradictions = [
            {"assertion_key": key, "positions": dict(pos)}
            for key, pos in sorted(positions.items()) if len(pos) > 1
        ]
        return {
            "contract": "edge.coordinator_result.v1", "execution": execution["execution"],
            "paid_calls": 0, "facts": buckets["FACT"], "weak_signals": buckets["WEAK_SIGNAL"],
            "inferences": buckets["INFERENCE"], "bets": buckets["BET"],
            "contradictions": contradictions, "verification": "unverified",
            "audit": execution["audit"], "task_results": execution["tasks"],
        }
