"""python -m searchlab "LEGO Pokemon" [--mode discovery|investigation] [--horizon FLIP|FUTURE_CLASSIC]
[--fixtures f.json] [--as-of ISO] [--out-dir data/searchlab]

Ecrit data/searchlab/<id>.json (public, sans capital) et met a jour index.json.
"""
import argparse
import json
import os
from datetime import datetime, timezone

from discovery.cli import build_adapters, watchlist_keys
from discovery.pipeline import run_pipeline
from edge_engine import load_config
from edge_io import atomic_write_json
from searchlab.planner import plan


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--mode", default="discovery", choices=["discovery", "investigation"])
    ap.add_argument("--horizon", default=None, choices=["FLIP", "FUTURE_CLASSIC"])
    ap.add_argument("--fixtures")
    ap.add_argument("--as-of")
    ap.add_argument("--out-dir", default=os.path.join("data", "searchlab"))
    ap.add_argument("--store-dir", default=os.path.join("data", "discovery", "store"))
    ap.add_argument("--private-dir", default=os.path.join("private", "searchlab"))
    ap.add_argument("--usd-to-eur", type=float)
    ap.add_argument("--plan-only", action="store_true")
    a = ap.parse_args(argv)
    camp = plan(a.query, a.mode, a.horizon)
    if a.plan_only:
        print(json.dumps(camp, ensure_ascii=False, indent=1))
        return camp
    config = load_config()
    as_of = datetime.fromisoformat(a.as_of) if a.as_of else datetime.now(timezone.utc)
    out_path = os.path.join(a.out_dir, f"{camp['id']}.json")
    usd = a.usd_to_eur or config.get("usd_to_eur")
    if not usd and not a.fixtures:
        from collect import USD_TO_EUR
        usd = USD_TO_EUR
    try:
        out, _, _ = run_pipeline([camp], build_adapters(a.fixtures, usd),
                                 config, a.store_dir, out_path, a.private_dir, as_of=as_of,
                                 watchlist_keys=watchlist_keys(), strategy=camp["strategy"])
        status = out["campaigns"][0]["status"]
    except Exception as e:  # la campagne echoue explicitement, jamais en silence
        out = {"campaign": camp, "posture": "NO_CONCLUSION", "error": type(e).__name__}
        atomic_write_json(out_path, out)
        status = "FAILED"
    idx_path = os.path.join(a.out_dir, "index.json")
    idx = {"schema_version": 1, "searches": []}
    if os.path.exists(idx_path):
        with open(idx_path, encoding="utf-8") as f:
            idx = json.load(f)
    idx["searches"] = [s for s in idx["searches"] if s["id"] != camp["id"]]
    idx["searches"].insert(0, {
        "id": camp["id"], "query": camp["user_query"], "mode": camp["mode"],
        "strategy": camp["strategy"], "at": as_of.isoformat(), "status": status,
        "posture": out.get("posture"), "simulated": out.get("simulated", False),
        "n_products": out.get("summary", {}).get("n_products", 0),
        "n_opportunity_alert": out.get("summary", {}).get("n_opportunity_alert", 0),
        "file": f"{camp['id']}.json"})
    idx["searches"] = idx["searches"][:100]
    atomic_write_json(idx_path, idx)
    print(json.dumps(idx["searches"][0], ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    main()
