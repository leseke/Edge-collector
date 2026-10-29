"""Public, static MRI report exporter. No network, no private input, no BUY signals."""
from datetime import datetime, timezone
import json
from pathlib import Path

PUBLIC_KEYS = {"case_id", "label", "as_of", "state", "thesis", "rival", "limitations", "source_urls"}
STATES = {"RESEARCH_ONLY", "PENDING", "NO_DATA", "SUPPORTED", "NOT_SUPPORTED"}

def export_public(cases, output_path):
    if not isinstance(cases, list):
        raise ValueError("cases must be list")
    public = []
    for case in cases:
        if not isinstance(case, dict) or set(case) != PUBLIC_KEYS:
            raise ValueError("unexpected private or omitted fields")
        if case["state"] not in STATES:
            raise ValueError("invalid state")
        if not all(isinstance(case[k], str) and 0 < len(case[k]) < 4000
                   for k in ("case_id", "label", "as_of", "thesis", "rival", "limitations")):
            raise ValueError("text fields invalid")
        ts = datetime.fromisoformat(case["as_of"].replace("Z", "+00:00"))
        if ts.tzinfo is None:
            raise ValueError("as_of must include timezone")
        if not isinstance(case["source_urls"], list) or any(
            not isinstance(u,str) or not u.startswith("https://") or len(u)>2048 for u in case["source_urls"]
        ):
            raise ValueError("source URLs invalid")
        public.append(dict(case))
    if len({x["case_id"] for x in public}) != len(public):
        raise ValueError("duplicate case ID")
    dest=Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"schema":"edge.mri.public.v1","cases":public},
                               ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return str(dest)

if __name__ == "__main__":
    # Intentionally no automatic export from sensitive raw investigation files.
    raise SystemExit("Use export_public with a curated allowlisted dataset.")
