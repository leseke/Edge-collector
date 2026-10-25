"""Unified private prospective evidence gate.

Claims about independent witness time and sold transactions are not proof.
Fail closed: no learning result is counted without trusted external verifiers.
"""
from intelligence.learning_prediction_bridge import evaluate_journal
from intelligence.learning_commitment_ledger import verified_commitments
from intelligence.prediction_journal import _records
from intelligence.sale_outcome_evidence_gate import examine_sale_evidence

def assess_prospective_learning(*,journal_path,ledger_path,sale_observations,as_of):
    events=_records(journal_path)
    predictions={x["id"]:x for x in events if x.get("type")=="PREDICTION"}
    commits=verified_commitments(ledger_path,predictions)
    preliminary=evaluate_journal(journal_path,commits,as_of=as_of)
    outcomes={x["prediction_id"]:x for x in events if x.get("type")=="OUTCOME"}
    audit=[]
    for commitment in commits:
        pid=commitment["prediction_id"]
        if pid not in outcomes:continue
        item=examine_sale_evidence(prediction=predictions[pid],outcome=outcomes[pid],
                                  observations=sale_observations.get(pid,[]),as_of=as_of)
        audit.append({"prediction_id":pid,"evidence_status":item["status"],
                      "market_outcome_proven":item["market_outcome_proven"]})
    return {"schema":"edge.learning.prospective_gate.v1",
            "internal_only":True,"preliminary":preliminary,
            "sale_evidence_review":audit,
            "verified_outcome_count":0,
            "external_witness_time_verified":False,
            "learning_improvement_demonstrated":False,
            "method_promotion_authorized":False,
            "investment_policy_changed":False,
            "status":"EVIDENCE_PENDING"}
