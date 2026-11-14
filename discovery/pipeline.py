"""Pipeline complet : Observation -> Candidat -> Investigation ->
Decision economique -> Financement -> Suivi historique.

Sorties :
- public  : data/discovery/latest.json (aucune donnee de capital)
- prive   : private/discovery/<run>/ (rapports avec financement)
"""
import os
from datetime import date, datetime, timezone

from discovery.campaigns import run_campaign
from discovery.signals import analyze
from discovery.store import CandidateStore
from edge_engine import assert_no_private_leak
from edge_io import append_jsonl, atomic_write_json
from investigation.analysis import investigate
from investigation.catalysts import evaluate_chain, load_catalysts, match
from investigation.fees import load_fee_profiles
from investigation.report import build_report, public_report, to_markdown


def _obs_for(rec):
    return [dict(o, id=o["obs_id"], source_url=o["url"]) for o in rec["observations"]]


def run_pipeline(campaigns, adapters, config, store_dir, public_path, private_dir,
                 as_of=None, watchlist_keys=(), catalysts=None, comparables=None,
                 fee_profile_name="conservative_default", strategy="FLIP",
                 max_total_calls=None, cost_journal_path=None, spend_guard=None):
    as_of_dt = as_of or datetime.now(timezone.utc)
    as_of_d = as_of_dt.date() if isinstance(as_of_dt, datetime) else as_of_dt
    stamp = as_of_dt.isoformat() if isinstance(as_of_dt, datetime) else as_of_d.isoformat()
    store = CandidateStore(store_dir)
    profiles = load_fee_profiles()
    profile = profiles[fee_profile_name]
    catalysts = load_catalysts() if catalysts is None else catalysts

    runs, all_candidates = [], []
    calls_left = max_total_calls
    for c in campaigns:
        if not c.get("enabled", True):
            continue
        if calls_left is not None:
            if calls_left <= 0:
                runs.append({"campaign_id": c["id"], "family": c["family"], "started_at": stamp,
                             "status": "SKIPPED_GLOBAL_BUDGET", "calls": [], "cost_units": 0})
                continue
            c = dict(c, max_calls=min(c.get("max_calls", 10), calls_left))
        if c.get("queries_from") == "store_revalidation":
            # Autant de candidats que le plafond permet d'interroger sur
            # TOUTES les sources : pas de travail planifie puis saute.
            per_query = max(1, len(c["sources"]))
            recs = store.to_revalidate(max(1, c.get("max_calls", 10) // per_query))
            if not recs:
                runs.append({"campaign_id": c["id"], "family": c["family"], "started_at": stamp,
                             "status": "SKIPPED_NOTHING_TO_REVALIDATE", "calls": [], "cost_units": 0})
                continue
            c = dict(c, queries=[r["product_key"].replace("lego:", "LEGO ") if r["product_key"].startswith("lego:")
                                 else r["name"] for r in recs])
        res = run_campaign(c, adapters, now=stamp)
        runs.append(res["run"])
        if calls_left is not None:
            calls_left -= res["run"].get("n_calls_executed", 0)
        if cost_journal_path:
            r = res["run"]
            append_jsonl(cost_journal_path, {
                "at": stamp, "campaign_id": r["campaign_id"], "status": r["status"],
                "calls_executed": r.get("n_calls_executed", 0), "errors": r.get("n_errors", 0),
                "cost_units": r["cost_units"],
                "duration_s": round(sum(x.get("duration_s", 0) for x in r["calls"]), 3),
                "by_source": {s: sum(1 for x in r["calls"] if x["source"] == s and x["status"] in ("OK", "EMPTY", "ERROR"))
                              for s in {x["source"] for x in r["calls"]}},
                "simulated": r.get("simulated", False)})
        if res["discovery"]:
            store.record_campaign(res)
            all_candidates.extend(res["discovery"]["candidates"])

    # Enrichit chaque produit vu dans ce run avec son historique stocke
    # (ventes conclues lors de runs precedents, y compris d'autres campagnes).
    seen_ids = {c["id"] for c in all_candidates}
    keys = {c["product_key"]: c for c in all_candidates}
    for key, ref in keys.items():
        for o in store.get(key)["observations"]:
            # seules les ventes conclues passees sont reutilisees : une
            # ancienne annonce n'est plus une offre achetable.
            if o["obs_id"] in seen_ids or o["evidence_type"] != "SOLD":
                continue
            seen_ids.add(o["obs_id"])
            all_candidates.append({
                "id": o["obs_id"], "product_key": key, "name": o["name"],
                "source": o["source"], "source_url": o["url"],
                "observed_at": o["observed_at"], "price_eur": o["price_eur"],
                "shipping_eur": o.get("shipping_eur"), "evidence_type": o["evidence_type"],
                "identity_confidence": ref["identity_confidence"],
                "seller_type": "UNKNOWN", "simulated": o.get("simulated", False)})
    groups = analyze(all_candidates, watchlist_keys,
                     config.get("discovery_policy"), as_of=as_of_d)
    investigations, public_items = [], []
    run_id = "run_" + stamp.replace(":", "").replace("-", "")[:15]
    rep_dir = os.path.join(private_dir, run_id)
    for g in groups:
        rec = store.get(g["product_key"])
        item = {k: g[k] for k in ("product_key", "names", "in_watchlist", "n_buyable", "n_sold",
                                  "sold_median_eur", "reasons", "risks", "needs_investigation",
                                  "simulated", "sources", "evidence_types")}
        item["candidate_id"] = rec["id"]
        item["first_seen"] = rec["first_seen"]
        item["origin_campaign"] = rec["origin_campaign"]
        if g["needs_investigation"]:
            obs = _obs_for(rec)
            # le meilleur prix achetable est recalcule sur l'historique complet
            cats = [evaluate_chain(c, g["names"][0], obs, as_of_d) for c in match(g["names"][0], catalysts)]
            inv = investigate(g, obs, as_of_d, config, profile, profile.get("verified", False),
                              strategy=strategy, comparables=(comparables or {}).get(g["product_key"]),
                              catalyst_evals=cats)
            report = build_report(inv, g["names"][0], as_of_d)
            store.record_evaluation(g["product_key"], stamp, inv["decision"], inv["confidence"]["level"],
                                    g["best_offer"]["total_eur"] if g["best_offer"] else None,
                                    report["sections"]["12_these"], inv["scenarios"], strategy)
            slug = g["product_key"].replace(":", "_").replace("+", "_")
            atomic_write_json(os.path.join(rep_dir, f"{slug}.json"), report)
            os.makedirs(rep_dir, exist_ok=True)
            with open(os.path.join(rep_dir, f"{slug}.md"), "w", encoding="utf-8") as f:
                f.write(to_markdown(report))
            item["investigation"] = {
                "decision": inv["decision"], "rationale": inv["rationale"],
                "confidence": inv["confidence"]["level"],
                "opportunity_alert": inv["opportunity_alert"],
                "report": public_report(report)}
            investigations.append(inv)
        public_items.append(item)

    # ---- Entonnoir : confirmation payante eventuelle (plafonnee) ----
    # L'autorisation vient UNIQUEMENT du garde (config privee), jamais de
    # la config fusionnee ni d'une definition de campagne.
    from investigation.funnel import eligible, query_for
    from investigation.spend import SpendGuard
    guard = spend_guard if spend_guard is not None else SpendGuard(None)
    elig = eligible(investigations)
    max_paid, why_paid = guard.max_calls, guard.public_reason  # jamais de montant publie
    paid_sources = [n for n, ad in adapters.items()
                    if getattr(ad, "paid", False) and getattr(ad, "guard", None) is guard]
    paid_info = {"eligible": elig, "max_calls": max_paid, "reason": why_paid,
                 "sources": paid_sources, "executed": False}
    queries = [q for q in (query_for(k) for k in elig) if q]
    if elig and max_paid > 0 and paid_sources and queries:
        guard.allow(queries[:max_paid])  # seules ces requetes pourront etre facturees
        conf = {"id": "paid-confirmation", "family": "liquidity", "queries": queries[:max_paid],
                "sources": paid_sources[:1], "max_calls": max_paid, "max_expansions": 0,
                "limit_per_query": 50}
        res = run_campaign(conf, adapters, now=stamp)
        runs.append(res["run"])
        paid_info["executed"] = True
        paid_info["calls_executed"] = res["run"].get("n_calls_executed", 0)
        if cost_journal_path:
            append_jsonl(cost_journal_path, {"at": stamp, "campaign_id": "paid-confirmation",
                                             "status": res["run"]["status"],
                                             "calls_executed": res["run"].get("n_calls_executed", 0),
                                             "cost_units": res["run"]["cost_units"],
                                             "paid": True, "budget": why_paid})
        if res["discovery"]:
            store.record_campaign(res)
    statuses = [r["status"] for r in runs]
    n_alert = sum(1 for i in investigations if i["opportunity_alert"])
    if n_alert:
        posture = "SIGNALS"
    elif not runs or all(s in ("FAILED", "INVALID_CONFIG", "SKIPPED_NOTHING_TO_REVALIDATE",
                               "SKIPPED_GLOBAL_BUDGET") for s in statuses):
        posture = "NO_CONCLUSION"
    elif any(s in ("PARTIAL", "FAILED", "NO_DATA", "INVALID_CONFIG", "SKIPPED_GLOBAL_BUDGET") for s in statuses
             if s != "SKIPPED_NOTHING_TO_REVALIDATE"):
        posture = "NO_CONCLUSION"
    else:
        posture = "NO_OPPORTUNITY_FOUND"
    out = {
        "schema_version": 1, "generated_at": stamp, "run_id": run_id,
        "simulated": any(r.get("simulated") for r in runs),
        "posture": posture,
        "campaigns": runs,
        "summary": {"n_campaigns": len(runs), "campaign_status": statuses,
                    "n_products": len(public_items),
                    "n_investigated": len(investigations), "n_opportunity_alert": n_alert,
                    "n_not_in_watchlist": sum(1 for p in public_items if not p["in_watchlist"])},
        "products": public_items,
        "paid_confirmation": paid_info,
    }
    assert_no_private_leak(out)
    atomic_write_json(public_path, out)
    return out, investigations, store
