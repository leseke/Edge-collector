"""Private prospective learning bridge.

Joins outcome records to predictions and pre-outcome paired method forecasts.
No correctness is derived from subjective notes; POSITIVE/NEGATIVE are labels
supplied by the outcome assessor, not independently verified market facts.
"""
from intelligence.prediction_journal import _records, _dt
from intelligence.private_learning_evaluation import evaluate_private_batch

def evaluate_journal(journal_path, commitments, *, as_of):
    cutoff=_dt(as_of)
    events=_records(journal_path)
    predictions={r["id"]:r for r in events if r.get("type")=="PREDICTION"}
    outcomes={r["prediction_id"]:r for r in events if r.get("type")=="OUTCOME"}
    if len(outcomes)!=sum(r.get("type")=="OUTCOME" for r in events):
        raise ValueError("duplicate outcome records")
    if not isinstance(commitments,list):raise ValueError("commitment list required")
    rows=[];used=set();excluded={"PENDING":0,"UNRESOLVED":0,"INVALID_HORIZON":0}
    for item in commitments:
        if not isinstance(item,dict) or set(item)!={"prediction_id","forecast_at","baseline_positive","challenger_positive"}:
            raise ValueError("strict commitment fields required")
        pid=item["prediction_id"]
        if not isinstance(pid,str) or pid in used:raise ValueError("duplicate or invalid commitment")
        used.add(pid)
        if any(type(item[k]) is not bool for k in ("baseline_positive","challenger_positive")):
            raise ValueError("boolean forecasts required")
        if pid not in predictions:raise ValueError("unknown prediction")
        prediction=predictions[pid]
        forecast=_dt(item["forecast_at"])
        if forecast>_dt(prediction["as_of"]) or forecast>cutoff:
            raise ValueError("forecast not precommitted at prediction cutoff")
        if pid not in outcomes or _dt(outcomes[pid]["observed_at"])>cutoff:
            excluded["PENDING"]+=1;continue
        outcome=outcomes[pid]
        if _dt(outcome["observed_at"])<_dt(prediction["due_at"]):
            excluded["INVALID_HORIZON"]+=1;continue
        if outcome["outcome"] not in {"POSITIVE","NEGATIVE"}:
            excluded["UNRESOLVED"]+=1;continue
        truth=outcome["outcome"]=="POSITIVE"
        rows.append({"case_id":pid,"baseline_correct":item["baseline_positive"]==truth,
                     "challenger_correct":item["challenger_positive"]==truth,"outcome_observed":True})
    report=evaluate_private_batch(rows)
    report["source"]="PREDICTION_JOURNAL_WITH_EXTERNAL_PRECOMMITMENTS"
    report["outcome_provenance_verified"]=False
    report["commitment_integrity_verified"]=False
    report["exclusions"]=excluded
    report["not_investment_advice"]=True
    return report
