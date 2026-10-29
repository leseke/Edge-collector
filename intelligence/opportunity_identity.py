"""EDGE Opportunity Intelligence V1: strict product identity, no fuzzy merging.

Distinct language, region, edition, state or identifier must not be equated.
Unknown identity elements prevent a confirmed comparison.
"""
import hashlib
import json
import re

KEYS={"category","brand","reference","edition","language","region","condition","sealed"}
CATEGORIES={"TCG","LEGO","OTHER"}
CONDITIONS={"NEW","USED","GRADED","NOT_APPLICABLE"}

def product_identity(record):
    if not isinstance(record,dict) or set(record)!=KEYS:
        raise ValueError("complete explicit product identity required")
    if record["category"] not in CATEGORIES or record["condition"] not in CONDITIONS:
        raise ValueError("invalid category/condition")
    if type(record["sealed"]) is not bool:
        raise ValueError("sealed must be boolean")
    for k in KEYS-{"sealed"}:
        if not isinstance(record[k],str) or not 1<=len(record[k].strip())<=100:
            raise ValueError("missing or invalid identity dimension")
    if record["condition"]=="USED" and record["sealed"]:
        raise ValueError("used product cannot be sealed in confirmed identity")
    d={k:re.sub(r"\s+"," ",record[k].strip()).casefold() if k not in {"sealed","category","condition"} else record[k] for k in KEYS}
    # An unknown qualifier is valid to store, but must never be treated as confirmed.
    known=all(d[k] not in {"unknown","inconnu","?"} for k in KEYS-{"sealed"})
    digest=hashlib.sha256(json.dumps(d,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return {"schema":"edge.product.identity.v1","identity":d,"key":digest[:24],
            "identity_complete":known}

def compare_identity(left,right):
    a=product_identity(left)
    b=product_identity(right)
    mismatches=sorted(k for k in KEYS if a["identity"][k]!=b["identity"][k])
    if mismatches:
        verdict="DIFFERENT"
    elif not a["identity_complete"] or not b["identity_complete"]:
        verdict="UNRESOLVED"
    else:
        verdict="SAME_EXACT"
    return {"verdict":verdict,"differences":mismatches,"financial_comparison_eligible":verdict=="SAME_EXACT"}
