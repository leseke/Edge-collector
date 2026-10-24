"""Build a reviewed research-only MRI preview from provenance-gated local fixtures.

No paid APIs, network access, financial action or implicit deployment.
Run: python -m tools.build_mri_preview
"""
import json
from pathlib import Path
from intelligence.historical_evidence_gate import qualify_case
from intelligence.mri_public_adapter import publish_reviewed_cases

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/"investigation/fixtures/mri_003_historical_evidence_cases.json"
OUTPUT=ROOT/"preview/data/mri_public.json"
LABELS={"pokemon-cn-2022":"Pokémon Chine — 2022","lego-10365-2025":"LEGO Black Pearl — 2025"}
LIMIT="Document historique retrouvé ultérieurement : aucune capture contemporaine qualifiée, aucune performance de revente démontrée."

def generate(source_path=INPUT,output_path=OUTPUT):
    raw=json.loads(Path(source_path).read_text(encoding="utf-8"))
    if raw.get("schema")!="edge.mri.historical_evidence_candidates.v1":
        raise ValueError("unexpected fixture schema")
    cases=raw.get("cases")
    if not isinstance(cases,list) or not cases:
        raise ValueError("missing cases")
    vetted=[]
    gates=[]
    for case in cases:
        result=qualify_case(case)
        if case["case_id"] not in LABELS:
            raise ValueError("case not editorially allowlisted")
        if result["replay_ready"]:
            raise ValueError("research-only preview cannot publish qualified replay as confirmed")
        urls=[x["url"] for x in case["sources"] if x["role"]=="pre_signal"]
        vetted.append({"case_id":case["case_id"],"label":LABELS[case["case_id"]],
                       "as_of":case["cutoff"],"thesis":case["hypothesis"],"rival":case["rival"],
                       "limitations":LIMIT,"source_urls":urls})
        gates.append(result)
    return publish_reviewed_cases(vetted,gates,output_path)

if __name__=="__main__":
    print(generate())
