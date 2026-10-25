"""Build and compare vetted MRI research public data without writing to production.

Usage: python -m tools.prepare_mri_public_release --output /tmp/mri-release
This command never contacts a network, commits, pushes or changes main.
"""
import argparse
import hashlib
import json
from pathlib import Path
from tools.build_mri_preview import generate

ROOT = Path(__file__).resolve().parents[1]
PUBLISHED = ROOT / "mri/data/mri_public.json"

def prepare(output_dir, currently_published=PUBLISHED):
    target = Path(output_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    candidate = target / "mri_public.json"
    generate(output_path=candidate)
    data = json.loads(candidate.read_text(encoding="utf-8"))
    assert data["schema"] == "edge.mri.public.v1"
    assert all(x["state"] == "RESEARCH_ONLY" for x in data["cases"])
    existing_path = Path(currently_published)
    existing = json.loads(existing_path.read_text(encoding="utf-8")) if existing_path.is_file() else None
    if existing is not None and existing.get("schema") != data["schema"]:
        raise ValueError("production schema mismatch; manual intervention required")
    normalized = lambda obj: json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    changed = existing is None or normalized(existing) != normalized(data)
    report = {
        "schema": "edge.mri.public.release_review.v1",
        "changed": changed,
        "candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        "public_cases": len(data["cases"]),
        "status": "REVIEW_REQUIRED" if changed else "UNCHANGED",
        "publication_performed": False,
        "purchase_authorized": False,
        "note": "Review this artifact; no direct write to main or Pages."
    }
    (target/"release_review.json").write_text(json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.output), sort_keys=True))
