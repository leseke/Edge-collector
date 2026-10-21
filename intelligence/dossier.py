"""Dossier d'enquete : plan, inventaire, contradictions, inconnues,
conformite, conditions d'actualisation. Immuable (ecriture exclusive),
public (aucune donnee privee, aucun texte tiers suspect republie)."""
import json
import os

from edge_engine import assert_no_private_leak
from intelligence.validator import FORBIDDEN_KEY_RE


class DossierExists(RuntimeError):
    pass


def dossier_relpath(report_id, version):
    return f"dossiers/{report_id}/v{version:04d}.json"


def _keys(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k
            yield from _keys(v)
    elif isinstance(o, list):
        for v in o:
            yield from _keys(v)


def check_dossier_public(dossier):
    assert_no_private_leak(dossier)
    bad = [k for k in _keys(dossier) if FORBIDDEN_KEY_RE.search(str(k))]
    if bad:
        raise ValueError(f"cle interdite dans le dossier : {bad}")


def write_dossier(root, dossier):
    """(AI-002A, conserve pour compatibilite) Ecriture seule du dossier.
    AI-002B : la publication passe par ReportStore.publish(report, dossier)."""
    check_dossier_public(dossier)
    rel = dossier_relpath(dossier["report_id"], dossier["report_version"])
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        raise DossierExists(rel) from None
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(dossier, f, ensure_ascii=False, sort_keys=True, indent=1)
        f.flush()
        os.fsync(f.fileno())
    return rel
