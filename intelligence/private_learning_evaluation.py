"""Private learning evaluation report; no UI exposure, no automatic promotion.

Paired held-out evaluation with minimum sample, disagreement accounting, and
fail-closed results. A gain is a research finding, never a policy change.
"""
import json
from pathlib import Path

def evaluate_private_batch(records, *, minimum=30):
    if type(minimum) is not int or minimum<30:raise ValueError("minimum sample too small")
    if not isinstance(records,list):raise ValueError("paired records required")
    ids=set();base=challenger=0;wins=losses=0
    for record in records:
        if not isinstance(record,dict) or set(record)!={"case_id","baseline_correct","challenger_correct","outcome_observed"}:
            raise ValueError("strict evaluation case required")
        i=record["case_id"]
        if not isinstance(i,str) or not i or i in ids:raise ValueError("invalid or repeated case")
        ids.add(i)
        if any(type(record[k]) is not bool for k in ("baseline_correct","challenger_correct","outcome_observed")):
            raise ValueError("boolean labels required")
        if not record["outcome_observed"]:raise ValueError("unresolved outcome cannot be scored")
        b=record["baseline_correct"];c=record["challenger_correct"]
        base+=b;challenger+=c;wins+=c and not b;losses+=b and not c
    n=len(records)
    status="INSUFFICIENT_EVIDENCE" if n<minimum else ("REVIEW_REQUIRED" if wins>losses else "NO_DEMONSTRATED_GAIN")
    return {"schema":"edge.learning.private_evaluation.v1","status":status,
        "cases":n,"baseline_correct":base,"challenger_correct":challenger,
        "challenger_only_correct":wins,"baseline_only_correct":losses,
        "requires_prospective_validation":True,"promotion_authorized":False,
        "ui_visibility":"INTERNAL_ONLY","investment_policy_changed":False}

def evaluate_private_file(input_path,output_path):
    source=json.loads(Path(input_path).read_text(encoding="utf-8"))
    if not isinstance(source,dict) or set(source)!={"schema","cases"} or source["schema"]!="edge.learning.holdout.v1":
        raise ValueError("invalid holdout package")
    report=evaluate_private_batch(source["cases"])
    out=Path(output_path);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return report
