"""Vues graphiques derivees UNIQUEMENT des donnees du rapport.

Aucune valeur n'est calculee, interpolee ni demandee a une IA : les points
manquants restent des trous, les estimations et simulations sont marquees.
"""


def chart_view(report, chart_id):
    ch = next(c for c in report["charts"] if c["chart_id"] == chart_id)
    ds = {d["dataset_id"]: d for d in report["datasets"]}
    src = {s["source_id"]: s for s in report["sources"]}
    series = []
    for did in ch["dataset_ids"]:
        d = ds[did]
        pts = []
        for p in d["points"]:
            style = {"measured": "solid", "estimated": "dashed", "simulated": "simulated", "missing": "gap"}[p["status"]]
            pts.append({"t": p["t"], "value": p["value"], "style": style})
        series.append({"dataset_id": did, "label": d["title"], "measure": d["measure"],
                       "simulated": d["simulated"], "points": pts,
                       "n_missing": sum(1 for p in d["points"] if p["status"] == "missing"),
                       "provenance": [{"source_id": i, "publisher": src[i]["publisher"], "url": src[i]["url"],
                                       "simulated": src[i]["simulated"]} for i in d["provenance"]["source_ids"]]})
    first = ds[ch["dataset_ids"][0]]
    return {"chart_id": chart_id, "type": ch["type"], "title": ch["title"],
            "unit": first["unit"], "currency": first["currency"], "territory": first["territory"],
            "watermark": "DONNEES SIMULEES" if any(s["simulated"] for s in series) else None,
            "series": series}
