"""Offline batch intake for previously obtained retail snapshots.

No network access. Each entry carries reviewed capture metadata and source
bytes loaded from a local file. Records never prove stock or completed sales.
"""
import json
from pathlib import Path
from intelligence.retail_capture_import import import_reviewed_capture

def import_capture_batch(*,manifest_path,journal_path,as_of):
    path=Path(manifest_path)
    data=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data,list) or not 1<=len(data)<=20:
        raise ValueError("bounded capture batch required")
    directory=path.resolve().parent
    prepared=[]
    for item in data:
        if not isinstance(item,dict) or set(item)!={"capture","snapshot_file"}:
            raise ValueError("strict batch entry required")
        filename=item["snapshot_file"]
        if not isinstance(filename,str) or "/" in filename or "\\" in filename or filename in (".",".."):
            raise ValueError("snapshot filename must be local basename")
        source=directory/filename
        if source.is_symlink() or not source.is_file() or source.stat().st_size>200000:
            raise ValueError("invalid capture file")
        body=source.read_bytes()
        prepared.append((item["capture"],body))
    # Validate all captures before writing any record by staging to a temporary journal.
    import tempfile
    from intelligence.retail_observation_history import _read
    with tempfile.TemporaryDirectory() as temp:
        staging=Path(temp)/"staged.jsonl"
        existing=Path(journal_path)
        if existing.exists():
            import shutil
            shutil.copyfile(existing,staging)
        results=[import_reviewed_capture(journal_path=staging,capture=c,as_of=as_of,snapshot_bytes=b)
                 for c,b in prepared]
        # Persist only after the complete batch has passed.
        existing.parent.mkdir(parents=True,exist_ok=True)
        import os
        swap=existing.with_name(existing.name+".edge-stage")
        if swap.exists():raise ValueError("staging path already exists")
        try:
            swap.write_bytes(staging.read_bytes())
            os.replace(swap,existing)
        finally:
            if swap.exists():swap.unlink()
    return {"schema":"edge.retail.capture_batch.v1","entries":len(results),
            "new_observations":sum(r["appended"] for r in results),
            "duplicates":sum(not r["appended"] for r in results),
            "source_authenticity_verified":False,"purchase_authorized":False}
