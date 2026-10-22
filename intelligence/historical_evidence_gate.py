"""MRI-003 historical evidence gate: do not backdate modern discoveries.

A publication date alone never proves an observation at that date. Historical
replays may only use sources with independently dated capture evidence.
No network, no investment decision, no model invocation.
"""
from datetime import datetime, timezone

ROLES = {"pre_signal", "later_event", "outcome_context"}
SUPPORT = {"contemporaneous_archive", "first_party_capture_log", "publisher_date_only", "modern_retrieval"}

def _dt(value):
    if not isinstance(value, str):
        raise ValueError("timestamp required")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone required")
    return result.astimezone(timezone.utc)

def classify_source(source, cutoff):
    """Return replay eligibility, with explicit evidentiary reason."""
    if not isinstance(source, dict):
        raise ValueError("source object required")
    for key in ("source_id", "url", "published_at", "retrieved_at", "role", "support"):
        if not isinstance(source.get(key), str) or not source[key].strip():
            raise ValueError("missing source field: " + key)
    if source["role"] not in ROLES or source["support"] not in SUPPORT:
        raise ValueError("unknown provenance classification")
    publication, retrieval, cut = _dt(source["published_at"]), _dt(source["retrieved_at"]), _dt(cutoff)
    if publication > cut:
        return {"source_id": source["source_id"], "eligible": False, "reason": "PUBLISHED_AFTER_CUTOFF"}
    if source["role"] != "pre_signal":
        return {"source_id": source["source_id"], "eligible": False, "reason": "NOT_A_PRE_SIGNAL"}
    if source["support"] not in {"contemporaneous_archive", "first_party_capture_log"}:
        return {"source_id": source["source_id"], "eligible": False, "reason": "NO_CONTEMPORANEOUS_CAPTURE"}
    captured = source.get("captured_at")
    if not isinstance(captured, str) or not captured.strip():
        return {"source_id": source["source_id"], "eligible": False, "reason": "MISSING_CAPTURE_TIMESTAMP"}
    if _dt(captured) > cut:
        return {"source_id": source["source_id"], "eligible": False, "reason": "CAPTURE_AFTER_CUTOFF"}
    if _dt(captured) < publication:
        return {"source_id": source["source_id"], "eligible": False, "reason": "CAPTURE_BEFORE_PUBLICATION"}
    if not isinstance(source.get("capture_url"), str) or not source["capture_url"].strip():
        return {"source_id": source["source_id"], "eligible": False, "reason": "MISSING_CAPTURE_PROVENANCE"}
    return {"source_id": source["source_id"], "eligible": True, "reason": "CAPTURE_WITHIN_CUTOFF"}

def qualify_case(case):
    if not isinstance(case, dict) or not isinstance(case.get("sources"), list):
        raise ValueError("case and sources required")
    cutoff = case["cutoff"]
    evaluations = [classify_source(x, cutoff) for x in case["sources"]]
    ids = [x["source_id"] for x in evaluations]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate source IDs")
    valid = [x["source_id"] for x in evaluations if x["eligible"]]
    return {"case_id": case["case_id"], "cutoff": cutoff,
            "replay_ready": bool(valid), "eligible_source_ids": valid,
            "source_audit": evaluations,
            "outcome_status": "NOT_ASSESSED",
            "financial_signal": "NOT_EVALUATED",
            "forecast_skill": "NOT_ESTABLISHED"}
