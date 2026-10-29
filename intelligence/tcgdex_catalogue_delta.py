"""Compare two validated TCGdex catalogue reports without price or sale inference."""
def compare_catalogue_snapshots(previous,current):
    for doc in (previous,current):
        if not isinstance(doc,dict) or doc.get("schema")!="edge.tcg.catalogue_review.v1":
            raise ValueError("validated catalogue required")
        if doc.get("coverage")!="SNAPSHOT_ONLY" or not doc.get("sets"):
            raise ValueError("incomplete catalogue")
    old={x["set_id"]:x["set_name"] for x in previous["sets"]}
    new={x["set_id"]:x["set_name"] for x in current["sets"]}
    if len(old)!=len(previous["sets"]) or len(new)!=len(current["sets"]):
        raise ValueError("duplicate identities")
    if previous["observed_at"]>=current["observed_at"]:
        raise ValueError("chronological snapshots required")
    return {"schema":"edge.tcg.catalogue_delta.v1",
      "previous_at":previous["observed_at"],"current_at":current["observed_at"],
      "added_sets":[{"id":k,"name":new[k]} for k in sorted(new.keys()-old.keys())],
      "removed_from_snapshot":[{"id":k,"name":old[k]} for k in sorted(old.keys()-new.keys())],
      "renamed_sets":[{"id":k,"previous":old[k],"current":new[k]} for k in sorted(old.keys()&new.keys()) if old[k]!=new[k]],
      "removal_proves_discontinuation":False,
      "new_set_proves_sealed_product":False,"market_sales_verified":False,
      "purchase_authorized":False}
