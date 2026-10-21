"""AI-002C — Evidence Discovery : collecte, qualification, integration.

edge.evidence_item.v1 : chaque element porte origine/URL, collecteur, date
d'observation, date de publication, statut de verification, limites de
reutilisation, empreinte de contenu, relation au sujet. Il distingue prix
affiche, prix public de detail, transaction conclue, estimation et simple
affirmation commerciale.

Principes :
- aucune promotion automatique : tout entre 'unverified', quelle que soit la
  reputation de l'editeur ; 'human_verified' exige une trace humaine ;
- une transaction conclue exige une preuve de transaction (enregistrement de
  vente d'une plateforme ou justificatif) : sinon c'est un prix affiche ;
- aucune valeur simulee dans un magasin reel ni dans un corpus reel ;
- le texte collecte est une donnee non fiable (signale, jamais execute) ;
- journal append-only rejouable : une interruption ne corrompt rien, une
  reprise est idempotente.
"""
import hashlib
import json
import math
import os
import re
from datetime import date, datetime, timedelta
from urllib.parse import urlsplit

from intelligence.compliance import suspicious
from intelligence.validator import CURRENCIES

SCHEMA = "edge.evidence_item.v1"
ORIGIN_KINDS = {"public_web", "manual_import", "edge_collector"}
METHODS = {"page_fetch", "search_snippet", "manual_entry", "collector_api"}
REUSE = {"quote_only", "summary_only", "full", "unknown"}
CLAIM_TYPES = {"fact", "commercial_claim", "estimate", "opinion"}
RELATIONS = {"supports", "contradicts", "context"}
MEAS_KINDS = {"asking_price", "retail_price", "sold_transaction", "estimate", "count"}
PRICE_KINDS = {"asking_price", "retail_price", "sold_transaction", "estimate"}
QUOTE_MAX_WORDS = 25
TEXT_MAX_CHARS = 300
# Champs facultatifs, strictement descriptifs : absence != egalite de perimetre.
SCOPE_FIELDS = ("territory", "language", "product_line", "edition", "definition", "period")


def _scope_relation(a, b):
    """Retourne (relation, raison) sans inférer un périmètre absent."""
    sa, sb = a.get("scope") or {}, b.get("scope") or {}
    differences = [f for f in SCOPE_FIELDS if sa.get(f) is not None and sb.get(f) is not None
                   and sa[f] != sb[f]]
    if differences:
        return "different_scope", differences
    unknown = [f for f in SCOPE_FIELDS if sa.get(f) is None or sb.get(f) is None]
    if unknown:
        return "ambiguous_scope", unknown
    return "same_scope", []


def _provenance_info(it):
    """Méthode constatée, non réputation de l'éditeur ni certification de vérité."""
    method = it["origin"]["method"]
    if method == "search_snippet":
        return {"collection_level": "search_excerpt_unconfirmed", "strong_evidence": False}
    if method == "page_fetch":
        return {"collection_level": "page_directly_read", "strong_evidence": False}
    if method == "collector_api":
        return {"collection_level": "collector_record_unverified", "strong_evidence": False}
    return {"collection_level": "manual_entry_unverified", "strong_evidence": False}



def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _dt(s):
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("fuseau requis")
    return d


def _valid_url(u):
    if not isinstance(u, str) or not u.startswith("https://"):
        return False
    p = urlsplit(u)
    return bool(p.netloc) and "." in p.netloc


def normalize_url(u):
    p = urlsplit(u)
    return f"https://{p.netloc.lower()}{p.path.rstrip('/') or '/'}" + (f"?{p.query}" if p.query else "")


def validate_item(it):
    E = []
    if not isinstance(it, dict) or it.get("schema") != SCHEMA:
        return ["schema edge.evidence_item.v1 attendu"]
    for k in ("subject_id", "topic_id", "relation", "assertion_key", "position", "origin", "observed_at",
              "published_at", "verification", "reuse", "content", "claim_type", "measurement", "simulated"):
        if k not in it:
            E.append(f"champ obligatoire absent : {k}")
    if E:
        return E
    if it["simulated"] is not False:
        E.append("element simule refuse : aucune valeur fictive dans une collecte reelle")
    o = it["origin"] or {}
    for k in ("kind", "url", "publisher", "collector_id", "method"):
        if k not in o:
            E.append(f"origin.{k} absent")
    if E:
        return E
    if o["kind"] not in ORIGIN_KINDS:
        E.append("origin.kind invalide")
    if o["method"] not in METHODS:
        E.append("origin.method invalide")
    if not o["collector_id"] or not isinstance(o["collector_id"], str):
        E.append("origin.collector_id requis")
    if o["url"] is None:
        if o["kind"] == "public_web":
            E.append("origin.url requise pour une source web publique")
    elif not _valid_url(o["url"]):
        E.append("origin.url : https:// et domaine valides requis")
    try:
        obs = _dt(it["observed_at"])
    except (ValueError, TypeError) as e:
        E.append(f"observed_at invalide ({e})")
        obs = None
    if it["published_at"] is not None:
        try:
            pub = date.fromisoformat(str(it["published_at"]))
            if obs and pub > obs.date():
                E.append("published_at posterieure a l'observation")
        except ValueError:
            E.append("published_at invalide")
    v = it["verification"]
    if v not in ("unverified", "human_verified"):
        E.append("verification : 'unverified' ou 'human_verified' uniquement (aucune promotion automatique)")
    elif v == "human_verified":
        vb = it.get("verified_by") or {}
        if vb.get("role") != "human" or not vb.get("id") or not vb.get("at"):
            E.append("human_verified exige verified_by {role: human, id, at}")
    r = it["reuse"] or {}
    if r.get("terms") not in REUSE:
        E.append("reuse.terms invalide")
    c = it["content"] or {}
    text = c.get("text")
    if not isinstance(text, str) or not text.strip() or len(text) > TEXT_MAX_CHARS:
        E.append(f"content.text requis (1 a {TEXT_MAX_CHARS} caracteres)")
    elif r.get("terms") in ("quote_only", "unknown") and len(text.split()) > QUOTE_MAX_WORDS:
        E.append(f"citation trop longue pour des droits '{r.get('terms')}' (max {QUOTE_MAX_WORDS} mots)")
    if not c.get("locator"):
        E.append("content.locator requis")
    if "sha256" in c and isinstance(text, str) and c["sha256"] != _sha(text):
        E.append("empreinte de contenu differente du texte")
    if "scope" in it:
        scope = it["scope"]
        if not isinstance(scope, dict) or set(scope) - set(SCOPE_FIELDS):
            E.append("scope : objet avec champs reconnus uniquement")
        elif any(v is not None and (not isinstance(v, str) or not v.strip()) for v in scope.values()):
            E.append("scope : valeurs non vides ou null")
    if it["claim_type"] not in CLAIM_TYPES:
        E.append("claim_type invalide")
    if it["relation"] not in RELATIONS:
        E.append("relation invalide")
    m = it["measurement"]
    if m is not None:
        E += _validate_measurement(m, it["claim_type"], obs)
    return E


def _validate_measurement(m, claim_type, obs):
    E = []
    kind = m.get("kind")
    if kind not in MEAS_KINDS:
        return [f"measurement.kind invalide {kind!r}"]
    val = m.get("value")
    if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val):
        E.append("measurement.value : nombre fini requis")
    elif val <= 0:
        E.append("measurement.value : strictement positif requis")
    if kind in PRICE_KINDS:
        if m.get("unit") != "currency" or m.get("currency") not in CURRENCIES:
            E.append(f"devise invalide ou absente ({m.get('currency')!r}) pour un prix")
    elif m.get("currency") is not None:
        E.append("devise renseignee pour une mesure non monetaire")
    p = m.get("period") or {}
    try:
        a, b = date.fromisoformat(p["start"]), date.fromisoformat(p["end"])
        if a > b:
            E.append("periode inversee")
        if obs and b > obs.date():
            E.append("periode posterieure a l'observation")
    except (KeyError, TypeError, ValueError):
        E.append("periode invalide")
    if not re.match(r"^([A-Z]{2}|EU|GLOBAL)$", str(m.get("territory"))):
        E.append("territoire invalide")
    if kind == "sold_transaction":
        te = m.get("transaction_evidence") or {}
        if te.get("kind") not in ("platform_sold_record", "receipt") or not _valid_url(te.get("url") or ""):
            E.append("transaction conclue sans preuve de transaction : c'est au mieux un prix affiche")
        if claim_type in ("commercial_claim", "opinion"):
            E.append("une affirmation commerciale ou une opinion ne prouve pas une transaction")
    if kind == "estimate" and claim_type != "estimate":
        E.append("measurement estimate exige claim_type estimate")
    if claim_type == "estimate" and kind != "estimate":
        E.append("claim_type estimate exige measurement estimate")
    q = m.get("quantity")
    if q is not None and (isinstance(q, bool) or not isinstance(q, int) or q < 1):
        E.append("quantity : entier >= 1 ou null")
    return E


def _append_line(path, line):
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())


class EvidenceStore:
    """Journal append-only rejouable (source de verite unique)."""

    def __init__(self, root):
        self.root = root
        self.ledger = os.path.join(root, "ledger.jsonl")

    def _events(self):
        evs, truncated = [], 0
        if not os.path.exists(self.ledger):
            return evs, truncated
        with open(self.ledger, encoding="utf-8") as f:
            for line in f:
                if not line.endswith("\n"):
                    truncated += 1  # ecriture interrompue : ignoree
                    continue
                if not line.strip():
                    continue
                try:
                    evs.append(json.loads(line))
                except ValueError:
                    truncated += 1
        return evs, truncated

    def integrity(self):
        evs, truncated = self._events()
        return {"events": len(evs), "truncated_lines": truncated}

    def _state(self):
        by_key, by_id = {}, {}
        for e in self._events()[0]:
            if e["event"] in ("accepted", "changed"):
                it = e["item"]
                key = (normalize_url(it["origin"]["url"]) if it["origin"]["url"] else "manual", it["content"]["locator"])
                by_key.setdefault(key, []).append(it)
                by_id[it["evidence_id"]] = it
        return by_key, by_id

    def items(self, include_superseded=False):
        by_key, _ = self._state()
        out = []
        for versions in by_key.values():
            out.extend(versions if include_superseded else versions[-1:])
        return out

    def history(self, url, locator):
        return self._state()[0].get((normalize_url(url), locator), [])

    def _seal_truncated_tail(self):
        """Apres une interruption, la derniere ligne peut etre tronquee (sans
        fin de ligne). On la cloture pour qu'elle reste une ligne invalide
        isolee : sinon la prochaine ecriture s'y collerait et serait perdue."""
        if os.path.exists(self.ledger) and os.path.getsize(self.ledger) > 0:
            with open(self.ledger, "rb") as f:
                f.seek(-1, os.SEEK_END)
                last = f.read(1)
            if last != b"\n":
                _append_line(self.ledger, "")

    def import_batch(self, items, batch_id, now):
        os.makedirs(self.root, exist_ok=True)
        self._seal_truncated_tail()
        res = {"batch_id": batch_id, "accepted": 0, "duplicates": 0, "changed": 0, "rejected": []}
        by_key, by_id = self._state()
        for i, raw in enumerate(items):
            it = json.loads(json.dumps(raw))  # copie
            errs = validate_item(it)
            if errs:
                res["rejected"].append({"index": i, "errors": errs})
                continue
            sha = _sha(it["content"]["text"])
            it["content"]["sha256"] = sha
            url = it["origin"]["url"]
            key = (normalize_url(url) if url else "manual", it["content"]["locator"])
            it["evidence_id"] = "ev_" + _sha(f"{key[0]}|{key[1]}|{sha}")[:16]
            it["flags"] = ["contenu_suspect"] if suspicious(it["content"]["text"]) else []
            it["imported_at"] = now.isoformat()
            it["batch_id"] = batch_id
            prev = by_key.get(key, [])
            if it["evidence_id"] in by_id or (prev and prev[-1]["content"]["sha256"] == sha):
                res["duplicates"] += 1
                continue
            kind = "changed" if prev else "accepted"
            if prev:
                it["flags"].append("page_modifiee")
                it["supersedes"] = prev[-1]["evidence_id"]
            _append_line(self.ledger, json.dumps({"event": kind, "item": it}, ensure_ascii=False, sort_keys=True))
            by_key.setdefault(key, []).append(it)
            by_id[it["evidence_id"]] = it
            res["changed" if prev else "accepted"] += 1
        return res


def qualify(items, now, required_topics=(), max_age_days=365):
    """Doublons de contenu (miroirs), pages modifiees, contradictions,
    mesures anciennes, sujets insuffisants. Aucune donnee n'est modifiee."""
    by_sha = {}
    for it in items:
        by_sha.setdefault(it["content"]["sha256"], []).append(it)
    mirrors = [{"sha256": s, "evidence_ids": [x["evidence_id"] for x in g],
                "urls": [x["origin"]["url"] for x in g]} for s, g in by_sha.items() if len(g) > 1]
    changed = [{"evidence_id": it["evidence_id"], "supersedes": it["supersedes"], "url": it["origin"]["url"]}
               for it in items if it.get("supersedes")]
    contradictions = []
    scope_reviews = []
    positions = {}
    for it in items:
        positions.setdefault((it["topic_id"], it["assertion_key"]), []).append(it)
    for (t, k), group in positions.items():
        valid = [it for it in group if it["position"] != "n/a"]
        for i, a in enumerate(valid):
            for b in valid[i + 1:]:
                if a["position"] == b["position"]:
                    continue
                relation, fields = _scope_relation(a, b)
                # Un extrait de recherche ne suffit pas à établir une contradiction.
                unconfirmed = any(x["origin"]["method"] == "search_snippet" for x in (a, b))
                verdict = "unresolved_evidence" if relation == "same_scope" and unconfirmed else relation
                row = {"type": "assertion", "topic_id": t, "assertion_key": k,
                       "evidence_ids": [a["evidence_id"], b["evidence_id"]],
                       "positions": [a["position"], b["position"]],
                       "verdict": verdict, "scope_fields": fields}
                if relation == "same_scope" and not unconfirmed:
                    contradictions.append(row)
                else:
                    scope_reviews.append(row)
    groups = {}
    for it in items:
        m = it["measurement"]
        if m and m["kind"] in PRICE_KINDS:
            groups.setdefault((m["kind"], m["territory"], m["currency"], m["period"]["start"], m["period"]["end"],
                               it["assertion_key"]), []).append((m["value"], it["evidence_id"]))
    for k, vals in groups.items():
        v = [x[0] for x in vals]
        if len(v) > 1 and max(v) > min(v) * 1.2:
            contradictions.append({"type": "numeric", "key": list(k), "values": vals})
    stale = []
    for it in items:
        m = it["measurement"]
        if m and (now.date() - date.fromisoformat(m["period"]["end"])) > timedelta(days=max_age_days):
            stale.append({"evidence_id": it["evidence_id"], "period_end": m["period"]["end"]})
    present = {it["topic_id"] for it in items if "contenu_suspect" not in it["flags"]}
    insufficient = sorted(set(required_topics) - present)
    reasons = []
    if not any(it["measurement"] and it["measurement"]["kind"] == "sold_transaction" for it in items):
        reasons.append("aucune vente conclue documentee : prix realises et volumes inconnus")
    if not any(it["verification"] == "human_verified" for it in items):
        reasons.append("aucune preuve verifiee par un humain")
    return {"mirrors": mirrors, "changed_pages": changed, "contradictions": contradictions,
            "scope_reviews": scope_reviews, "provenance_reviews": [dict(evidence_id=it["evidence_id"], **_provenance_info(it)) for it in items],
            "stale_measurements": stale, "insufficient_topics": insufficient, "insufficient_reasons": reasons,
            "flagged_suspicious": [it["evidence_id"] for it in items if "contenu_suspect" in it["flags"]]}


MEASURE_MAP = {"asking_price": "asking_price", "retail_price": "retail_price", "sold_transaction": "sold_price",
               "estimate": "other", "count": "volume"}


def build_corpus(items, spec, data_as_of):
    """Corpus edge.corpus.v1 REEL a partir d'elements qualifies. Refuse tout
    element simule. Exclut le contenu suspect et les doublons de contenu
    (garde le premier observe). Sources toujours 'unverified' sauf trace humaine."""
    if any(it.get("simulated") for it in items):
        raise ValueError("element simule : un corpus reel ne melange jamais fictif et reel")
    usable, seen = [], set()
    for it in sorted(items, key=lambda x: x["observed_at"]):
        if "contenu_suspect" in it["flags"] or it["content"]["sha256"] in seen:
            continue
        seen.add(it["content"]["sha256"])
        usable.append(it)
    if not usable:
        raise ValueError("aucun element exploitable")
    sources, extracts, series = {}, [], {}
    for it in usable:
        o = it["origin"]
        sid = "src_" + _sha(normalize_url(o["url"]) if o["url"] else o["collector_id"])[:12]
        if sid not in sources:
            sources[sid] = {"source_id": sid, "title": f"{o['publisher']} ({o['method']})", "publisher": o["publisher"],
                            "url": o["url"], "published_at": it["published_at"], "accessed_at": it["observed_at"][:10],
                            "tier": "secondary" if it["verification"] == "human_verified" else "unverified",
                            "simulated": False, "notes": f"reutilisation : {it['reuse']['terms']} ; collecteur {o['collector_id']} ; provenance : {_provenance_info(it)['collection_level']} (non verifiee)"}
        extracts.append({"extract_id": "ext_" + it["evidence_id"][3:], "source_id": sid, "topic_id": it["topic_id"],
                         "assertion_key": it["assertion_key"], "position": it["position"],
                         "observed_on": it["observed_at"][:10], "statement": it["content"]["text"],
                         "claim_type": it["claim_type"]})
        m = it["measurement"]
        if m:
            k = (m["kind"], m["territory"], m["currency"], it["topic_id"])
            series.setdefault(k, []).append((m["period"]["end"], m["value"], sid, m["period"]["start"]))
    datasets, dtopics = [], {}
    for (kind, terr, cur, topic), pts in series.items():
        pts.sort()
        # une date = un point : deux mesures le meme jour ne sont pas fusionnees silencieusement
        dates = [p[0] for p in pts]
        if len(set(dates)) != len(dates):
            raise ValueError(f"mesures multiples a la meme date pour {kind}/{terr} : a arbitrer avant integration")
        did = "ds_" + _sha(f"{kind}|{terr}|{cur}|{topic}")[:12]
        datasets.append({"dataset_id": did, "title": f"{kind} {terr} ({cur or 'unite'}) — observations collectees",
                         "unit": "currency" if cur else "count", "currency": cur, "measure": MEASURE_MAP[kind],
                         "territory": terr, "period": {"start": min(p[3] for p in pts), "end": pts[-1][0]},
                         "frequency": "irregular",
                         "provenance": {"source_ids": sorted({p[2] for p in pts}), "method": "observations collectees",
                                        "collected_by": "human"},
                         "simulated": False,
                         "points": [{"t": p[0], "value": p[1], "status": "estimated" if kind == "estimate" else "measured"}
                                    for p in pts]})
        dtopics[did] = [topic]
    return {"corpus_schema": "edge.corpus.v1", "corpus_id": spec["corpus_id"], "simulated": False,
            "data_as_of": data_as_of, "subject": spec["subject"], "freshness": spec.get("freshness"),
            "entities": spec["entities"], "topics": spec["topics"], "sources": list(sources.values()),
            "datasets": datasets, "dataset_topics": dtopics, "extracts": extracts}


# ------------------------------------------------------------ collecteurs

class PublicWebCollector:
    """Collecteur web PREPARE, NON ACTIVE. Exige registre 'public_web' VERIFIED
    et un domaine explicitement autorise. Aucun contournement (robots, CGU)."""
    collector_id = "public_web"

    def __init__(self, transport=None, registry=None):
        from discovery.access import load_registry
        self.registry = registry if registry is not None else load_registry()
        self.transport = transport

    def fetch(self, url):
        from discovery.adapters import SourceUnavailable
        cfg = self.registry.get("public_web") or {}
        if cfg.get("status") != "VERIFIED" or self.transport is None:
            raise SourceUnavailable("collecteur web public non active (registre public_web non VERIFIED)")
        if not _valid_url(url) or urlsplit(url).netloc.lower() not in set(cfg.get("allowed_domains", [])):
            raise ValueError("domaine non autorise par le registre")
        return self.transport.get(url)  # erreur HTTP propagee : aucune donnee inventee


def from_discovery_candidate(c, subject_id, topic_id, now, publisher=None):
    """Collecteurs existants -> preuve. Ventes : uniquement depuis une source
    d'enregistrement de ventes (SOLD) ; donnee simulee : ignoree (None)."""
    if c.get("simulated"):
        return None
    kinds = {"SOLD": "sold_transaction", "ASKING_PRICE": "asking_price", "RETAIL_OFFER": "asking_price"}
    k = kinds.get(c.get("evidence_type"))
    if k is None:
        return None
    m = {"kind": k, "value": c["price_eur"], "unit": "currency", "currency": "EUR",
         "period": {"start": c["observed_at"][:10], "end": c["observed_at"][:10]}, "territory": "GLOBAL",
         "quantity": 1 if k == "sold_transaction" else None,
         "transaction_evidence": {"kind": "platform_sold_record", "url": c["source_url"]} if k == "sold_transaction" else None}
    return {"schema": SCHEMA, "subject_id": subject_id, "topic_id": topic_id, "relation": "supports",
            "assertion_key": f"{k}:{c['id']}", "position": "n/a",
            "origin": {"kind": "edge_collector", "url": c["source_url"], "publisher": publisher or c["source"],
                       "collector_id": f"discovery:{c['source']}", "method": "collector_api"},
            "observed_at": c["observed_at"], "published_at": None, "verification": "unverified",
            "reuse": {"terms": "unknown", "license": None, "notes": "donnee de collecteur EDGE"},
            "content": {"text": str(c.get("name", ""))[:200] or k, "language": "und", "locator": str(c["id"])},
            "claim_type": "fact", "measurement": m, "simulated": False}
