"""Unified private prospective evidence gate.

Claims about independent witness time and sold transactions are not proof.
Fail closed: no learning result is counted without trusted external verifiers.
"""
from intelligence.learning_prediction_bridge import evaluate_journal
from intelligence.learning_commitment_ledger import verified_commitments
from intelligence.prediction_journal import _records
from intelligence.sale_outcome_evidence_gate import examine_sale_evidence
from intelligence.sales_source_typing import classify_sales_observations

def assess_prospective_learning(*,journal_path,ledger_path,sale_observations,as_of,typed_sale_observations=None):
    if not isinstance(sale_observations,dict):raise ValueError('sale observations must be keyed by prediction')
    typed_sale_observations={} if typed_sale_observations is None else typed_sale_observations
    if not isinstance(typed_sale_observations,dict):raise ValueError('typed observations must be keyed by prediction')
    events=_records(journal_path)
    predictions={x["id"]:x for x in events if x.get("type")=="PREDICTION"}
    commits=verified_commitments(ledger_path,predictions)
    preliminary=evaluate_journal(journal_path,commits,as_of=as_of)
    outcomes={x["prediction_id"]:x for x in events if x.get("type")=="OUTCOME"}
    audit=[]; typed_audit=[]
    for commitment in commits:
        pid=commitment["prediction_id"]
        if pid not in outcomes:continue
        item=examine_sale_evidence(prediction=predictions[pid],outcome=outcomes[pid],
                                  observations=sale_observations.get(pid,[]),as_of=as_of)
        typed_records=typed_sale_observations.get(pid,[])
        typed_report=classify_sales_observations(typed_records,as_of=as_of)
        if any(x["product_key"]!=predictions[pid]["product_key"] for x in typed_records):
            raise ValueError("typed sale product identity mismatch")
        typed_audit.append({"prediction_id":pid,"source_types":typed_report["counts"],
                            "independently_verified_sales":typed_report["verified_transactions"]})
        audit.append({"prediction_id":pid,"evidence_status":item["status"],
                      "market_outcome_proven":item["market_outcome_proven"]})
    return {"schema":"edge.learning.prospective_gate.v1",
            "internal_only":True,"preliminary":preliminary,
            "sale_evidence_review":audit,"typed_sales_review":typed_audit,
            "verified_outcome_count":0,
            "external_witness_time_verified":False,
            "learning_improvement_demonstrated":False,
            "method_promotion_authorized":False,
            "investment_policy_changed":False,
            "status":"EVIDENCE_PENDING"}
