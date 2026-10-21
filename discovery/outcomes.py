"""Evaluation a posteriori des anticipations (apprentissage mesure).

Regles anti-biais :
- cohorte figee : TOUTES les decisions initiales anterieures a
  as_of - horizon sont evaluees, y compris celles qu'on n'a plus suivies
  (elles comptent en UNRESOLVED, jamais exclues silencieusement) ;
- la decision et le prix de reference initiaux sont ceux enregistres a
  l'epoque (store.initial, jamais reecrit) ;
- groupe temoin : les candidats evalues WAIT/WATCH permettent de
  verifier si les signaux font mieux que l'absence de signal ;
- en dessous de min_sample resolus, aucune conclusion n'est tiree.
"""
from datetime import date, timedelta

from discovery.signals import quantile
from investigation.fees import economics


def evaluate(store, as_of, horizon_days, fee_profile, window_days=30,
             hit_roi_pct=20, min_sample=20):
    rows = []
    for rec in store.state["candidates"].values():
        init = rec.get("initial")
        if not init or init.get("reference_price_eur") is None:
            continue
        t0 = date.fromisoformat(init["at"][:10])
        if t0 + timedelta(days=horizon_days) > as_of:
            continue
        target = t0 + timedelta(days=horizon_days)
        later = [o["price_eur"] for o in rec["observations"]
                 if o["evidence_type"] == "SOLD"
                 and abs((date.fromisoformat(o["observed_at"][:10]) - target).days) <= window_days]
        row = {"id": rec["id"], "product_key": rec["product_key"],
               "family": rec["origin_family"], "campaign": rec["origin_campaign"],
               "initial_decision": init["decision"], "decided_at": init["at"],
               "reference_price_eur": init["reference_price_eur"],
               "simulated": rec.get("simulated", False)}
        if len(later) < 3:
            row["outcome"] = "UNRESOLVED"
            row["why"] = f"{len(later)} vente(s) conclue(s) autour de l'horizon (<3)"
        else:
            sale = quantile(later, 0.5)
            eco = economics(init["reference_price_eur"], 0, sale, fee_profile, horizon_days)
            row.update(realized=eco)
            roi = eco["net_roi_pct"]
            row["outcome"] = "HIT" if roi >= hit_roi_pct else ("LOSS" if roi < 0 else "FLAT")
        rows.append(row)

    def agg(key):
        out = {}
        for r in rows:
            g = out.setdefault(r[key], {"n": 0, "resolved": 0, "HIT": 0, "FLAT": 0, "LOSS": 0, "UNRESOLVED": 0, "roi": []})
            g["n"] += 1
            g[r["outcome"]] += 1
            if r["outcome"] != "UNRESOLVED":
                g["resolved"] += 1
                g["roi"].append(r["realized"]["net_roi_pct"])
        for g in out.values():
            rois = g.pop("roi")
            g["median_net_roi_pct"] = round(quantile(rois, 0.5), 1) if rois else None
            g["hit_rate"] = round(g["HIT"] / g["resolved"], 3) if g["resolved"] else None
            g["conclusive"] = g["resolved"] >= min_sample
        return out

    n_resolved = sum(1 for r in rows if r["outcome"] != "UNRESOLVED")
    return {
        "as_of": as_of.isoformat(), "horizon_days": horizon_days,
        "cohort_size": len(rows), "resolved": n_resolved,
        "conclusive": n_resolved >= min_sample,
        "warning": None if n_resolved >= min_sample else
            f"echantillon insuffisant ({n_resolved} resolus < {min_sample}) : aucune conclusion d'apprentissage",
        "by_decision": agg("initial_decision"), "by_family": agg("family"),
        "by_campaign": agg("campaign"), "rows": rows,
    }
