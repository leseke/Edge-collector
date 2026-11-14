"""Sonde TCGdex : UNE recherche reelle, detail limite, preuves controlees.

Usage (depuis une machine avec acces Internet) :
    python -m tools.tcgdex_probe --query pikachu --details 2

Pre-requis : tcgdex en status VERIFIED dans discovery/sources_access.json.
Ecrit dans private/tcgdex_probe/<horodatage>/ (ignore par git) :
  raw/              reponses brutes (corps JSON, URL, parametres, date)
  latest.json       sortie du pipeline (identique au format public)
  cost_journal.jsonl
  probe_report.json schema, HTTP, controles de decision
--export-fixture copie les reponses brutes dans tests/fixtures/tcgdex_live/
pour un test de non-regression sur reponse reelle (donnees de cartes,
aucune donnee personnelle).
Aucun appel payant ; aucune autre source n'est activee.
"""
import argparse
import glob
import json
import os
import shutil
import sys
from datetime import datetime, timezone

from discovery.access import GatedAdapter, access_status, load_registry
from discovery.adapters_official import RequestsTransport, TcgdexAdapter, validate_card_pricing
from discovery.pipeline import run_pipeline
from discovery.recording_http import RecordingCachingTransport
from edge_engine import load_config
from edge_io import atomic_write_json

FIXTURE_DIR = os.path.join("tests", "fixtures", "tcgdex_live")


def probe(query, details, out_dir, inner_transport=None, as_of=None, registry=None):
    reg = registry or load_registry()
    st = access_status("tcgdex", reg, environ={})
    if not st["usable"]:
        raise SystemExit(f"tcgdex non activable : {st['reason']}")
    as_of = as_of or datetime.now(timezone.utc)
    http = RecordingCachingTransport(inner_transport or RequestsTransport(), os.path.join(out_dir, "raw"))
    adapter = TcgdexAdapter(http=http, max_details=details)
    live = inner_transport is None
    if not live:
        # Transport injecte (fixtures, tests) : jamais presente comme du reel.
        from discovery.fixture_http import SimulatedMarker
        adapter = SimulatedMarker(adapter)
    gated = GatedAdapter("tcgdex", adapter, reg, {})
    camp = {"id": "probe-tcgdex", "family": "emerging", "queries": [query], "sources": ["tcgdex"],
            "max_calls": 1, "max_expansions": 0, "limit_per_query": details}
    out, invs, _ = run_pipeline([camp], {"tcgdex": gated}, load_config(),
                                os.path.join(out_dir, "store"), os.path.join(out_dir, "latest.json"),
                                os.path.join(out_dir, "reports"), as_of=as_of,
                                cost_journal_path=os.path.join(out_dir, "cost_journal.jsonl"))
    # Controle de schema sur chaque reponse de detail brute
    schema = {}
    for f in glob.glob(os.path.join(out_dir, "raw", "*.json")):
        with open(f, encoding="utf-8") as fh:
            rec = json.load(fh)
        if "/cards/" in rec["url"]:
            schema[rec["url"].rsplit("/", 1)[-1]] = validate_card_pricing(rec["body"])
    decisions = {i["product_key"]: i["decision"] for i in invs}
    positive = {k: v for k, v in decisions.items() if v in ("BUY", "STRONG_BUY")}
    report = {
        "generated_at": as_of.isoformat(), "query": query, "max_details": details,
        "http": http.summary(),
        "campaign_status": [r["status"] for r in out["campaigns"]],
        "products": [{k: p.get(k) for k in ("product_key", "evidence_types", "n_buyable", "risks")}
                     for p in out["products"]],
        "schema_issues_by_card": schema,
        "decisions": decisions,
        "check_no_positive_decision_from_market_trend": not positive,
        "check_only_market_trend": all(p.get("evidence_types") == ["MARKET_TREND"] for p in out["products"]),
        "simulated": out["simulated"],
        "live": live,
    }
    atomic_write_json(os.path.join(out_dir, "probe_report.json"), report)
    return report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="pikachu")
    ap.add_argument("--details", type=int, default=2, help="requetes de detail max (1 a 5)")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--export-fixture", action="store_true")
    a = ap.parse_args(argv)
    if not 1 <= a.details <= 5:
        raise SystemExit("--details doit etre entre 1 et 5")
    out_dir = a.out_dir or os.path.join("private", "tcgdex_probe",
                                        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    try:
        rep = probe(a.query, a.details, out_dir)
    except SystemExit:
        raise
    except Exception as e:
        print(f"ECHEC de la sonde : {type(e).__name__}: {str(e)[:200]}")
        return 1
    h = rep["http"]
    print(f"Requetes HTTP executees : {h['http_requests_executed']} (cache : {h['served_from_cache']}) ; erreurs : {len(h['errors'])}")
    for r in h["requests"]:
        print(f"  {r['method']} {r['url']} {r['params'] or ''} -> {r['status']} {'(cache)' if r['from_cache'] else ''} {r.get('error', '')}")
    print("Anomalies de schema :", json.dumps(rep["schema_issues_by_card"], ensure_ascii=False))
    print("Decisions :", rep["decisions"] or "aucune investigation (aucune offre achetable)")
    print("Aucune decision positive fondee sur MARKET_TREND :", rep["check_no_positive_decision_from_market_trend"])
    print(f"Collecte reelle : {rep['live']} ; donnees simulees : {rep['simulated']}")
    print(f"Sortie : {out_dir}")
    if a.export_fixture:
        os.makedirs(FIXTURE_DIR, exist_ok=True)
        for f in glob.glob(os.path.join(out_dir, "raw", "*.json")):
            shutil.copy(f, FIXTURE_DIR)
        print(f"Reponses brutes copiees dans {FIXTURE_DIR} (a relire avant commit)")
    return 0 if rep["check_no_positive_decision_from_market_trend"] else 2


if __name__ == "__main__":
    sys.exit(main())
