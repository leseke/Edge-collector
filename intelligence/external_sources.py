"""Contrat de recherche externe edge.external_source.v1 (PREPARE, NON ACTIVE).

Toute page ou fichier recupere a l'avenir sera enregistre ainsi avant d'entrer
dans un corpus : URL et provenance, date de collecte, extraits exacts utilises
(localises, empreinte facultative), disponibilite, droits de reutilisation,
cout de recuperation (une recuperation payante exige une reservation R4.2),
confiance, conflits. Le texte reste une donnee NON FIABLE ; une source
externe entre au mieux en 'unverified'.
"""
import re
from datetime import datetime

REUSE = {"quote_only", "summary_only", "full", "unknown"}
CONFIDENCE = {"low", "medium", "high"}


class ExternalSourceRejected(ValueError):
    pass


def validate_record(r):
    E = []
    req = ("schema", "record_id", "url", "provenance", "collected_at", "availability", "rights",
           "retrieval_cost", "confidence", "conflicts_with", "extracts", "publisher", "title", "published_at")
    for k in req:
        if k not in r:
            E.append(f"champ obligatoire absent : {k}")
    if E:
        return E
    if r["schema"] != "edge.external_source.v1":
        E.append("schema inattendu")
    if not re.match(r"^xs_[a-z0-9][a-z0-9_.-]{1,63}$", str(r["record_id"])):
        E.append("record_id invalide")
    if not str(r["url"]).startswith("https://"):
        E.append("url : https:// requis")
    try:
        if datetime.fromisoformat(str(r["collected_at"])).tzinfo is None:
            E.append("collected_at : fuseau requis")
    except ValueError:
        E.append("collected_at invalide")
    av = r["availability"]
    if not isinstance(av.get("available"), bool):
        E.append("availability.available booleen requis")
    if r["rights"].get("reuse") not in REUSE:
        E.append(f"rights.reuse hors de {sorted(REUSE)}")
    c = r["retrieval_cost"]
    if c.get("paid") and not c.get("reservation_id"):
        E.append("recuperation payante sans reservation R4.2")
    if r["confidence"] not in CONFIDENCE:
        E.append("confidence invalide")
    if not r["extracts"]:
        E.append("au moins un extrait exact requis")
    for e in r["extracts"]:
        if not str(e.get("extract_id", "")).startswith("ext_") or not e.get("text") or not e.get("locator"):
            E.append(f"extrait invalide {e.get('extract_id')!r}")
    if r["rights"].get("reuse") == "unknown" and any(len(e.get("text", "")) > 300 for e in r["extracts"]):
        E.append("droits inconnus : extraits limites a des citations courtes (300 caracteres)")
    return E


def to_corpus_entries(r, accessed_on):
    """-> (source, extraits) pour un corpus edge.corpus.v1. Toujours 'unverified'."""
    errs = validate_record(r)
    if errs:
        raise ExternalSourceRejected("; ".join(errs))
    sid = "src_" + r["record_id"][3:]
    src = {"source_id": sid, "title": r["title"], "publisher": r["publisher"], "url": r["url"],
           "published_at": r["published_at"], "accessed_at": accessed_on, "tier": "unverified",
           "simulated": False, "notes": f"collecte externe {r['record_id']} ; droits : {r['rights']['reuse']}"}
    exts = [{"extract_id": e["extract_id"], "source_id": sid, "topic_id": e["topic_id"],
             "assertion_key": e.get("assertion_key", e["extract_id"]), "position": e.get("position", "n/a"),
             "observed_on": accessed_on, "statement": e["text"]} for e in r["extracts"]]
    return src, exts
