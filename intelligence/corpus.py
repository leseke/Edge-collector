"""Corpus AUTORISE d'une enquete : sources, datasets, extraits de sources.

Tout corpus est valide a l'entree (refus systematique des donnees non
conformes) en reutilisant le validateur EDGE Intelligence : un corpus qui ne
pourrait pas produire un rapport valide est rejete avant tout usage.
Le texte des extraits est une DONNEE NON FIABLE (sources tierces) : il n'est
jamais interprete comme une consigne.
"""
import hashlib
import json
import re
from datetime import date

from edge_engine import assert_no_private_leak
from intelligence import SCHEMA_ID, SCHEMA_VERSION
from intelligence.validator import FORBIDDEN_KEY_RE, assess, canonical_json

CORPUS_SCHEMA = "edge.corpus.v1"
_ID = re.compile(r"^[a-z0-9][a-z0-9_.-]{1,63}$")


class CorpusRejected(ValueError):
    pass


class Corpus:
    def __init__(self, d, sha):
        self.raw = d
        self.sha256 = sha
        self.corpus_id = d["corpus_id"]
        self.simulated = d["simulated"]
        self.subject = d["subject"]
        self.freshness = d.get("freshness") or {}
        self.data_as_of = d["data_as_of"]
        self.entities = d["entities"]
        self.topics = {t["topic_id"]: t for t in d["topics"]}
        self.sources = {s["source_id"]: s for s in d["sources"]}
        self.datasets = {x["dataset_id"]: x for x in d["datasets"]}
        self.dataset_topics = d["dataset_topics"]
        self.extracts = {e["extract_id"]: e for e in d["extracts"]}

    def datasets_for(self, topic_id):
        return [self.datasets[i] for i, ts in self.dataset_topics.items() if topic_id in ts]

    def extracts_for(self, topic_id):
        return [e for e in self.extracts.values() if e["topic_id"] == topic_id]


def _walk_keys(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk_keys(v)


def load_corpus_dict(d):
    errs = []
    if not isinstance(d, dict) or d.get("corpus_schema") != CORPUS_SCHEMA:
        raise CorpusRejected("corpus_schema edge.corpus.v1 attendu")
    for k in ("corpus_id", "simulated", "data_as_of", "subject", "entities", "topics", "sources",
              "datasets", "dataset_topics", "extracts"):
        if k not in d:
            errs.append(f"champ obligatoire absent : {k}")
    if errs:
        raise CorpusRejected("; ".join(errs))
    bad_keys = sorted({k for k in _walk_keys(d) if FORBIDDEN_KEY_RE.search(str(k))})
    if bad_keys:
        raise CorpusRejected(f"donnee privee ou d'allocation interdite : {bad_keys}")
    try:
        assert_no_private_leak(d)
    except ValueError as e:
        raise CorpusRejected(str(e)) from None
    if not isinstance(d["corpus_id"], str) or not _ID.match(d["corpus_id"]):
        errs.append("corpus_id invalide")
    if not isinstance(d["simulated"], bool):
        errs.append("simulated doit etre booleen")
    if not d["entities"] or not all(isinstance(x, str) and x.strip() for x in d["entities"]):
        errs.append("entities : liste de libelles non vides requise")
    topic_ids = [t.get("topic_id") for t in d["topics"]]
    if len(set(topic_ids)) != len(topic_ids) or not all(isinstance(t, str) and _ID.match(t) for t in topic_ids):
        errs.append("topics : identifiants invalides ou dupliques")
    for t in d["topics"]:
        if not isinstance(t.get("question"), str) or not t["question"].strip() or not t.get("keywords"):
            errs.append(f"topic {t.get('topic_id')} : question et keywords requis")
    ds_ids = {x.get("dataset_id") for x in d["datasets"]}
    for i, ts in d["dataset_topics"].items():
        if i not in ds_ids:
            errs.append(f"dataset_topics : dataset inconnu {i!r}")
        for t in ts:
            if t not in topic_ids:
                errs.append(f"dataset_topics : sujet inconnu {t!r}")
    src_ids = {s.get("source_id") for s in d["sources"]}
    ext_ids = []
    for e in d["extracts"]:
        ext_ids.append(e.get("extract_id"))
        if not isinstance(e.get("extract_id"), str) or not e["extract_id"].startswith("ext_"):
            errs.append(f"extrait : identifiant invalide {e.get('extract_id')!r}")
        if e.get("source_id") not in src_ids:
            errs.append(f"extrait {e.get('extract_id')} : source inconnue {e.get('source_id')!r}")
        if e.get("topic_id") not in topic_ids:
            errs.append(f"extrait {e.get('extract_id')} : sujet inconnu {e.get('topic_id')!r}")
        st = e.get("statement")
        if not isinstance(st, str) or not st.strip() or len(st) > 1000:
            errs.append(f"extrait {e.get('extract_id')} : enonce invalide")
        if e.get("claim_type") is not None and e["claim_type"] not in ("fact", "commercial_claim", "estimate", "opinion"):
            errs.append(f"extrait {e.get('extract_id')} : claim_type invalide")
        for k in ("assertion_key", "position"):
            if not isinstance(e.get(k), str) or not e[k]:
                errs.append(f"extrait {e.get('extract_id')} : {k} requis")
        try:
            date.fromisoformat(str(e.get("observed_on")))
        except ValueError:
            errs.append(f"extrait {e.get('extract_id')} : observed_on invalide")
    if len(set(ext_ids)) != len(ext_ids):
        errs.append("extraits dupliques")
    if errs:
        raise CorpusRejected("; ".join(errs[:8]))
    # Sources et datasets : verifies par le validateur EDGE via un rapport-sonde.
    created = max([d["data_as_of"]] + [s["accessed_at"] + "T23:59:59+00:00" for s in d["sources"]])
    probe = {"schema": SCHEMA_ID, "schema_version": SCHEMA_VERSION, "report_id": "eir_corpus-probe",
             "report_version": 1, "supersedes": None, "created_at": created, "data_as_of": d["data_as_of"],
             "production_status": "draft", "simulated": d["simulated"], "subject": d["subject"],
             "sources": d["sources"], "claims": [], "datasets": d["datasets"], "charts": [],
             "economics": {"listed_price_dataset_ids": [], "realized_sale_dataset_ids": [],
                           "availability": {"buyable_verified": False, "evidence_claim_ids": []},
                           "fees": {"claim_ids": [], "verified": False}, "liquidity": {"claim_ids": []},
                           "roi_hypotheses": [], "supply_demand_claim_ids": []},
             "decisions": {"agent_opinion": None, "edge_decision": {"decision": "NOT_EVALUATED", "decided_by": "none",
                                                                    "rules_applied": [], "evidence_refs": [], "decided_at": None}},
             "history": {"previous_versions": [], "related_report_ids": [], "changes": [], "corrections": [],
                         "conclusion_changes": []}}
    if d.get("freshness") is not None:
        probe["freshness"] = d["freshness"]
    try:
        a = assess(probe)
    except (TypeError, KeyError, ValueError) as e:
        raise CorpusRejected(f"corpus structurellement invalide : {type(e).__name__}") from None
    if not a["valid"]:
        raise CorpusRejected("sources/datasets non conformes : " + "; ".join(a["errors"][:5]))
    try:
        sha = hashlib.sha256(canonical_json(d).encode("utf-8")).hexdigest()
    except ValueError:
        raise CorpusRejected("nombre non fini") from None
    return Corpus(d, sha)


def load_corpus(path):
    with open(path, encoding="utf-8") as f:
        try:
            d = json.load(f)
        except ValueError as e:
            raise CorpusRejected(f"JSON invalide : {e}") from None
    return load_corpus_dict(d)
