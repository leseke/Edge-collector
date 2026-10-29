"""Review a downloaded TCGdex French catalogue snapshot, without network access.

Usage: python -m tools.review_tcgdex_catalogue --input sets.json --observed-at 2026-10-29T20:00:00Z
"""
import argparse
import json
from pathlib import Path
from intelligence.tcgdex_catalogue_review import inspect_tcgdex_sets

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--observed-at",required=True)
    args=p.parse_args(argv)
    path=Path(args.input)
    if not path.is_file() or path.is_symlink() or path.stat().st_size>1_000_000:
        raise ValueError("invalid catalogue file")
    result=inspect_tcgdex_sets(path.read_bytes(),observed_at=args.observed_at)
    summary={k:result[k] for k in ("schema","source","observed_at","source_snapshot_sha256","set_count","coverage","market_offer_evidence","completed_sale_verified","purchase_authorized")}
    print(json.dumps(summary,ensure_ascii=False,sort_keys=True))
    return summary

if __name__=="__main__":
    main()
