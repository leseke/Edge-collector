"""Calculs DETERMINISTES realises par EDGE (jamais par le modele).

Chaque calcul conserve sa methode, ses entrees exactes et son resultat ; le
validateur le recalcule a chaque controle : un resultat altere est detecte.
Une citation ne rend pas un calcul correct : seul le recalcul le fait.
"""
from datetime import date

METHODS = {"pct_change", "difference", "mean", "min", "max"}
TOLERANCE = 0.05  # ecart toleré sur un resultat annonce (arrondi a 1 decimale)


class ComputationError(ValueError):
    pass


def window_points(dataset, t_from, t_to):
    a, b = date.fromisoformat(t_from), date.fromisoformat(t_to)
    if a > b:
        raise ComputationError("fenetre inversee")
    pts = [p for p in dataset["points"] if a <= date.fromisoformat(p["t"]) <= b and p["value"] is not None]
    return [{"t": p["t"], "value": p["value"]} for p in pts]


def compute(method, dataset, t_from, t_to):
    if method not in METHODS:
        raise ComputationError(f"methode inconnue {method!r}")
    pts = window_points(dataset, t_from, t_to)
    vals = [p["value"] for p in pts]
    if method in ("pct_change", "difference"):
        if len(vals) < 2:
            raise ComputationError("au moins deux points requis")
        first, last = vals[0], vals[-1]
        if method == "pct_change":
            if first == 0:
                raise ComputationError("division par zero")
            res, unit = (last - first) / first * 100, "percent"
        else:
            res, unit = last - first, dataset["unit"]
    else:
        if not vals:
            raise ComputationError("aucun point dans la fenetre")
        res = {"mean": sum(vals) / len(vals), "min": min(vals), "max": max(vals)}[method]
        unit = dataset["unit"]
    return {"inputs": pts, "result": round(res, 6), "unit": unit,
            "currency": dataset["currency"] if unit == "currency" else None}


def representations(value):
    """Ecritures admises d'un resultat dans un texte (arrondis 0/1/2 decimales,
    signe ou valeur absolue)."""
    out = set()
    for v in (value, abs(value)):
        for nd in (0, 1, 2):
            s = f"{v:.{nd}f}"
            out.add(s)
            out.add(s.lstrip("-"))
    return out
