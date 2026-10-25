"""Learning pipeline: acquire and queue source packets without inventing lessons.

Review candidates must be manually authored and evaluated separately.
No source text is executed or accepted as instructions; no external network.
"""
import hashlib
import json
from pathlib import Path
from intelligence.learning_acquisition import intake_public_study
from intelligence.learning_library import library_summary

FIELDS={"source_url","published_at","observed_at","title","text"}

def stage_sources(input_path, output_path, *, library_path=None):
    raw=json.loads(Path(input_path).read_text(encoding="utf-8"))
    if not isinstance(raw,dict) or set(raw)!={"schema","documents"} or raw["schema"]!="edge.learning.source_batch.v1":
        raise ValueError("invalid input batch")
    docs=raw["documents"]
    if not isinstance(docs,list) or len(docs)>50:raise ValueError("invalid batch size")
    output=[];seen=set();failures=[]
    for i,doc in enumerate(docs):
        try:
            if not isinstance(doc,dict) or set(doc)!=FIELDS:raise ValueError("strict source fields required")
            candidate=intake_public_study(**doc)
            fingerprint=(candidate["source_url"],candidate["text_sha256"])
            if fingerprint in seen:continue
            seen.add(fingerprint)
            output.append(candidate)
        except (ValueError,TypeError,OverflowError) as exc:
            failures.append({"index":i,"error_type":type(exc).__name__})
    package={"schema":"edge.learning.intake_review.v1",
       "status":"REVIEW_REQUIRED" if output else "NO_VALID_SOURCES",
       "source_count":len(output),"failures":failures,
       "sources":output,"lessons_proposed":0,"lessons_adopted":0,
       "learning_applied":False,"changes_investment_policy":False}
    if library_path is not None:
        package["library_summary"]=library_summary(library_path,as_of=max((x["observed_at"] for x in output),default="1970-01-01T00:00:00Z"))
    dest=Path(output_path);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(package,sort_keys=True,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return package

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--input",required=True);p.add_argument("--output",required=True)
    a=p.parse_args();d=stage_sources(a.input,a.output)
    print(d["status"],d["source_count"],len(d["failures"]))
