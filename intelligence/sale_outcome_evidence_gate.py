"""Evidence gate for prospective outcomes.

A declared sale is not independently verified merely because a source URL exists.
Only independently checked evidence may be counted as corroborated; this module
cannot establish that marketplace records are authentic on its own.
"""
from datetime import timezone
from intelligence.prediction_journal import _dt

def examine_sale_evidence(*,prediction,outcome,observations,as_of):
    cutoff=_dt(as_of)
    if prediction.get("type")!="PREDICTION" or outcome.get("type")!="OUTCOME" or outcome.get("prediction_id")!=prediction.get("id"):
        raise ValueError("matching prediction and outcome required")
    if _dt(outcome["observed_at"])>cutoff or _dt(outcome["observed_at"])<_dt(prediction["due_at"]):
        raise ValueError("outcome outside admissible window")
    if outcome["outcome"] not in ("POSITIVE","NEGATIVE"):
        return {"status":"UNRESOLVED","corroborated":False,"observations_checked":0,"eligible_for_learning":False}
    if not isinstance(observations,list):raise ValueError("observations required")
    relevant=[];ids=set()
    for item in observations:
        if not isinstance(item,dict) or set(item)!={"evidence_id","source_url","product_key","sold_at","sale_price_eur","independently_verified"}:
            raise ValueError("strict observation fields required")
        evid=item["evidence_id"]
        if not isinstance(evid,str) or not evid or evid in ids:raise ValueError("duplicate evidence")
        ids.add(evid)
        if item["product_key"]!=prediction["product_key"]:continue
        if not isinstance(item["source_url"],str) or not item["source_url"].startswith("https://"):
            raise ValueError("HTTPS provenance required")
        if not isinstance(item["sale_price_eur"],(int,float)) or isinstance(item["sale_price_eur"],bool) or not 0<item["sale_price_eur"]<1e9:
            raise ValueError("positive sale price required")
        if _dt(item["sold_at"])>cutoff:raise ValueError("future sale")
        if type(item["independently_verified"]) is not bool:raise ValueError("verification must be boolean")
        relevant.append(item)
    linked=set(outcome["evidence_ids"])
    corroborated=[x for x in relevant if x["evidence_id"] in linked and x["independently_verified"]]
    return {"schema":"edge.learning.sale_evidence_review.v1",
            "status":"NEEDS_INDEPENDENT_AUDIT" if not corroborated else "DECLARED_VERIFIED_REQUIRES_TRUSTED_AUDIT",
            "corroborated":False,"declared_verified_count":len(corroborated),
            "observations_checked":len(relevant),"eligible_for_learning":False,
            "market_outcome_proven":False,"purchase_authorized":False}
