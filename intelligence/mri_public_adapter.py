"""Explicit, fail-closed adapter from MRI research records to public-only cases.

No implicit raw-record export. The caller must provide editorially approved
public case content and a matching reviewed MRI gate result.
"""
from intelligence.public_mri_export import export_public

def build_public_cases(reviewed_cases, gate_results):
    if not isinstance(reviewed_cases, list) or not isinstance(gate_results, list):
        raise ValueError("lists required")
    gates={g["case_id"]:g for g in gate_results if isinstance(g,dict) and "case_id" in g}
    if len(gates)!=len(gate_results):
        raise ValueError("duplicate or malformed gate result")
    result=[]
    for item in reviewed_cases:
        if not isinstance(item,dict) or set(item)!={"case_id","label","as_of","thesis","rival","limitations","source_urls"}:
            raise ValueError("reviewed public fields required, extra fields forbidden")
        gate=gates.get(item["case_id"])
        if gate is None:
            raise ValueError("missing evidence gate")
        if gate.get("financial_signal")!="NOT_EVALUATED":
            raise ValueError("financial signal must not be surfaced")
        if gate.get("replay_ready") is not False:
            raise ValueError("only research-only cases can be exposed in this stage")
        result.append({**item,"state":"RESEARCH_ONLY"})
    return result

def publish_reviewed_cases(reviewed_cases, gate_results, output_path):
    return export_public(build_public_cases(reviewed_cases,gate_results),output_path)
