"""Validateur strict des EDGE Intelligence Reports v1.

1. Structure : interprete le JSON Schema publie (sous-ensemble : type, enum,
   const, pattern, required, properties, additionalProperties, items,
   minimum, minLength, maxLength, minItems, anyOf). Pas de divergence
   possible entre le schema et le code.
2. Semantique EDGE : references croisees, dates, devises/unites, nombres
   finis, provenance, simulation, versionnement, politique d'allocation.
3. Niveau de verification calcule (jamais declare par l'auteur).
"""
import hashlib
import json
import math
import os
import re
from datetime import date, datetime, timedelta, timezone

from intelligence import SCHEMA_ID

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema", "edge_intelligence_report.v1.schema.json")
with open(SCHEMA_PATH, encoding="utf-8") as _f:
    SCHEMA = json.load(_f)

# ISO 4217 (sous-ensemble utile ; extensible par version mineure du schema)
CURRENCIES = {"EUR", "USD", "CNY", "JPY", "GBP", "HKD", "TWD", "KRW", "CHF", "CAD", "AUD", "SGD"}
PRICE_MEASURES = {"asking_price", "sold_price", "retail_price", "market_trend"}
POSITIVE = {"BUY", "STRONG_BUY"}
# Politique prudente quand le rapport n'en declare pas : au-dela, les
# donnees sont presentees comme perimees a la consultation.
DEFAULT_MAX_DATA_AGE_DAYS = 30
# Aucun montant d'allocation ni donnee financiere privee dans un rapport.
FORBIDDEN_KEY_RE = re.compile(r"(allocation|treasury|engaged|capital|budget|amount_authorized)", re.I)


# ------------------------------------------------------------ structure

def _type_ok(v, t):
    if t == "object":
        return isinstance(v, dict)
    if t == "array":
        return isinstance(v, list)
    if t == "string":
        return isinstance(v, str)
    if t == "boolean":
        return isinstance(v, bool)
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if t == "null":
        return v is None
    raise ValueError(t)


def check_schema(v, sch, path="$", errors=None):
    errors = [] if errors is None else errors
    if "anyOf" in sch:
        if not any(not check_schema(v, s, path, []) for s in sch["anyOf"]):
            errors.append(f"{path}: ne correspond a aucune forme autorisee")
        return errors
    if "const" in sch and v != sch["const"]:
        errors.append(f"{path}: valeur attendue {sch['const']!r}")
        return errors
    if "enum" in sch and v not in sch["enum"]:
        errors.append(f"{path}: {v!r} hors de {sch['enum']}")
        return errors
    if "type" in sch:
        types = sch["type"] if isinstance(sch["type"], list) else [sch["type"]]
        if not any(_type_ok(v, t) for t in types):
            errors.append(f"{path}: type {type(v).__name__} au lieu de {types}")
            return errors
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if not math.isfinite(v):
            errors.append(f"{path}: nombre non fini")
        elif "minimum" in sch and v < sch["minimum"]:
            errors.append(f"{path}: < {sch['minimum']}")
    if isinstance(v, str):
        if "minLength" in sch and len(v) < sch["minLength"]:
            errors.append(f"{path}: trop court")
        if "maxLength" in sch and len(v) > sch["maxLength"]:
            errors.append(f"{path}: trop long")
        if "pattern" in sch and not re.search(sch["pattern"], v):
            errors.append(f"{path}: format invalide ({v!r})")
    if isinstance(v, dict):
        for k in sch.get("required", []):
            if k not in v:
                errors.append(f"{path}.{k}: champ obligatoire absent")
        props = sch.get("properties", {})
        for k, val in v.items():
            if k in props:
                check_schema(val, props[k], f"{path}.{k}", errors)
            elif sch.get("additionalProperties") is False:
                errors.append(f"{path}.{k}: champ non autorise")
    if isinstance(v, list):
        if "minItems" in sch and len(v) < sch["minItems"]:
            errors.append(f"{path}: au moins {sch['minItems']} element(s)")
        if "items" in sch:
            for i, it in enumerate(v):
                check_schema(it, sch["items"], f"{path}[{i}]", errors)
    return errors


# ------------------------------------------------------------ utilitaires

def canonical_json(report):
    return json.dumps(report, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def content_sha256(report):
    return hashlib.sha256(canonical_json(report).encode("utf-8")).hexdigest()


def _dt(s):
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("fuseau horaire absent")
    return d


def _walk_numbers(o, path="$"):
    if isinstance(o, bool):
        return
    if isinstance(o, (int, float)):
        if not math.isfinite(o):
            yield path
    elif isinstance(o, dict):
        for k, v in o.items():
            yield from _walk_numbers(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _walk_numbers(v, f"{path}[{i}]")


def _walk_keys(o, path="$"):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k, f"{path}.{k}"
            yield from _walk_keys(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _walk_keys(v, f"{path}[{i}]")


# ------------------------------------------------------------ semantique

def check_semantics(r):
    E, W = [], []
    for p in _walk_numbers(r):
        E.append(f"{p}: nombre non fini (NaN/Infinity)")
    for k, p in _walk_keys(r):
        if FORBIDDEN_KEY_RE.search(k):
            E.append(f"{p}: champ interdit (allocation/donnee financiere privee : jamais dans un rapport)")
    try:
        created, as_of = _dt(r["created_at"]), _dt(r["data_as_of"])
        if as_of > created:
            E.append("$.data_as_of: posterieur a created_at")
    except (ValueError, TypeError) as e:
        E.append(f"$.created_at/data_as_of: date invalide ({e})")
        created = as_of = None

    def uniq(items, key, label):
        ids = [x[key] for x in items]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            E.append(f"$.{label}: identifiants dupliques {sorted(dup)}")
        return {x[key]: x for x in items}

    sources = uniq(r["sources"], "source_id", "sources")
    claims = uniq(r["claims"], "claim_id", "claims")
    datasets = uniq(r["datasets"], "dataset_id", "datasets")
    uniq(r["charts"], "chart_id", "charts")

    def ref(ids, table, label):
        for i in ids:
            if i not in table:
                E.append(f"{label}: reference inconnue {i!r}")

    # --- sources
    for s in r["sources"]:
        p = f"$.sources[{s['source_id']}]"
        try:
            acc = date.fromisoformat(s["accessed_at"])
            if created and acc > created.date():
                E.append(f"{p}.accessed_at: posterieur a created_at")
            if s["published_at"] and date.fromisoformat(s["published_at"]) > acc:
                E.append(f"{p}.published_at: posterieur a la consultation")
        except ValueError as e:
            E.append(f"{p}: date invalide ({e})")
        if s["url"] is not None and not str(s["url"]).startswith("https://"):
            E.append(f"{p}.url: https:// requis (ou null)")
        if not s["simulated"] and s["url"] is None and s["tier"] != "unverified":
            E.append(f"{p}: source reelle sans URL ne peut pas etre primary/secondary")

    # --- claims
    for c in r["claims"]:
        p = f"$.claims[{c['claim_id']}]"
        ref(c["source_ids"], sources, p + ".source_ids")
        ref(c.get("contradicting_source_ids", []), sources, p + ".contradicting_source_ids")
        cited = [sources[i] for i in c["source_ids"] if i in sources]
        if c["verification"] == "verified":
            if c["kind"] != "fact":
                E.append(f"{p}: seul un fait peut etre 'verified' ({c['kind']})")
            if not cited:
                E.append(f"{p}: fait 'verified' sans source")
            if any(s["simulated"] for s in cited):
                E.append(f"{p}: 'verified' avec une source simulee")
            if cited and all(s["tier"] == "unverified" for s in cited):
                E.append(f"{p}: 'verified' sans source primaire ou secondaire")
        if any(s["simulated"] for s in cited) and c["verification"] != "simulated":
            E.append(f"{p}: cite une source simulee -> verification doit etre 'simulated'")
        if c["verification"] == "contradicted" and not c.get("contradicting_source_ids"):
            E.append(f"{p}: 'contradicted' sans contradicting_source_ids")
        if c.get("source_claim_type") is not None and c["kind"] != "fact":
            E.append(f"{p}: source_claim_type reserve aux faits cites")
        rec = c.get("verification_record")
        if rec is not None:
            if c["verification"] != "verified" or c["kind"] != "fact":
                E.append(f"{p}: trace de verification sur une affirmation non verifiee")
            ev_ids = [e["source_id"] for e in rec["evidence"]]
            if not ev_ids:
                E.append(f"{p}.verification_record: aucune preuve citee")
            for sid in ev_ids:
                if sid not in c["source_ids"] or sid not in sources:
                    E.append(f"{p}.verification_record: preuve {sid!r} absente des sources de l'affirmation")
                elif sources[sid]["simulated"]:
                    E.append(f"{p}.verification_record: preuve simulee")
            try:
                vat = _dt(rec["verified_at"])
                if created and vat > created:
                    E.append(f"{p}.verification_record.verified_at: posterieur a created_at")
                for sid in ev_ids:
                    if sid in sources and vat.date() < date.fromisoformat(sources[sid]["accessed_at"]):
                        E.append(f"{p}.verification_record.verified_at: anterieur a la consultation de la preuve {sid}")
            except (ValueError, TypeError) as e:
                E.append(f"{p}.verification_record.verified_at: date invalide ({e})")
        elif c["verification"] == "verified":
            W.append(f"{p}: verification non documentee (aucune verification_record)")
        if c["kind"] == "invalidated":
            if not c.get("invalidated_by") or not c.get("invalidation_reason"):
                E.append(f"{p}: conclusion infirmee sans invalidated_by et invalidation_reason")
            elif c["invalidated_by"] not in claims:
                E.append(f"{p}.invalidated_by: reference inconnue")

    # --- datasets
    for d in r["datasets"]:
        p = f"$.datasets[{d['dataset_id']}]"
        ref(d["provenance"]["source_ids"], sources, p + ".provenance")
        prov = [sources[i] for i in d["provenance"]["source_ids"] if i in sources]
        if d["unit"] == "currency":
            if d["currency"] not in CURRENCIES:
                E.append(f"{p}.currency: {d['currency']!r} non reconnue (ISO 4217 attendu)")
        elif d["currency"] is not None:
            E.append(f"{p}: devise renseignee pour une unite {d['unit']!r}")
        if d["measure"] in PRICE_MEASURES and d["unit"] != "currency":
            E.append(f"{p}: mesure de prix {d['measure']!r} sans unite monetaire")
        if any(s["simulated"] for s in prov) and not d["simulated"]:
            E.append(f"{p}: provenance simulee mais dataset non simule")
        try:
            start, end = date.fromisoformat(d["period"]["start"]), date.fromisoformat(d["period"]["end"])
            if start > end:
                E.append(f"{p}.period: debut posterieur a la fin")
        except ValueError as e:
            E.append(f"{p}.period: date invalide ({e})")
            continue
        prev = None
        for i, pt in enumerate(d["points"]):
            pp = f"{p}.points[{i}]"
            try:
                t = date.fromisoformat(pt["t"])
            except ValueError:
                E.append(f"{pp}.t: date invalide")
                continue
            if not start <= t <= end:
                E.append(f"{pp}.t: hors periode")
            if as_of and t > as_of.date():
                E.append(f"{pp}.t: posterieur a data_as_of")
            if prev and t <= prev:
                E.append(f"{pp}.t: dates non strictement croissantes")
            prev = t
            v, st = pt["value"], pt["status"]
            if (v is None) != (st == "missing"):
                E.append(f"{pp}: valeur nulle <=> statut 'missing'")
            if st == "missing" and not pt.get("missing_reason"):
                E.append(f"{pp}: donnee manquante sans missing_reason")
            if d["simulated"] and st not in ("simulated", "missing"):
                E.append(f"{pp}: dataset simule mais point {st!r} (une simulation n'est jamais une mesure)")
            if not d["simulated"] and st == "simulated":
                E.append(f"{pp}: point simule dans un dataset reel")
            if st == "measured" and not prov:
                E.append(f"{pp}: mesure sans provenance")
            if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):
                if d["unit"] in ("currency", "count", "units") and v < 0:
                    E.append(f"{pp}: valeur negative pour l'unite {d['unit']!r}")
                if d["unit"] == "percent" and v < -100:
                    E.append(f"{pp}: pourcentage < -100")

    # --- interpretations et calculs (1.2)
    comps = {}
    for cm in r.get("computations", []) or []:
        p = f"$.computations[{cm['computation_id']}]"
        if cm["computation_id"] in comps:
            E.append(f"{p}: identifiant duplique")
        comps[cm["computation_id"]] = cm
        d = datasets.get(cm["dataset_id"])
        if d is None:
            E.append(f"{p}: dataset inconnu")
            continue
        from intelligence.computations import ComputationError, compute
        try:
            redo = compute(cm["method"], d, cm["t_from"], cm["t_to"])
        except (ComputationError, ValueError) as e:
            E.append(f"{p}: calcul impossible ({e})")
            continue
        if redo["inputs"] != cm["inputs"]:
            E.append(f"{p}: entrees du calcul differentes des donnees du dataset")
        if abs(redo["result"] - cm["result"]) > 1e-6:
            E.append(f"{p}: calcul errone (recalcul {redo['result']} != {cm['result']})")
        if (redo["unit"], redo["currency"]) != (cm["unit"], cm["currency"]):
            E.append(f"{p}: unite ou devise du calcul incoherente")
    for c in r["claims"]:
        p = f"$.claims[{c['claim_id']}]"
        b = c.get("basis")
        if c["kind"] == "interpretation":
            if c["verification"] == "verified":
                E.append(f"{p}: une interpretation n'est jamais 'verified'")
            if not b or not (b["fact_claim_ids"] or b["computation_ids"]):
                E.append(f"{p}: interpretation sans fondement (basis)")
        elif b is not None:
            E.append(f"{p}: basis reserve aux interpretations")
        if b:
            for i in b["fact_claim_ids"]:
                if i not in claims or claims[i]["kind"] != "fact":
                    E.append(f"{p}.basis: fait inconnu {i!r}")
            for i in b["computation_ids"]:
                if i not in comps:
                    E.append(f"{p}.basis: calcul inconnu {i!r}")

    # --- graphiques
    for ch in r["charts"]:
        p = f"$.charts[{ch['chart_id']}]"
        ref(ch["dataset_ids"], datasets, p)
        ds = [datasets[i] for i in ch["dataset_ids"] if i in datasets]
        if len({(x["unit"], x["currency"]) for x in ds}) > 1:
            E.append(f"{p}: series d'unites ou de devises differentes sur un meme axe")

    # --- economie
    ec = r["economics"]
    ref(ec["listed_price_dataset_ids"], datasets, "$.economics.listed_price_dataset_ids")
    ref(ec["realized_sale_dataset_ids"], datasets, "$.economics.realized_sale_dataset_ids")
    for i in ec["listed_price_dataset_ids"]:
        if i in datasets and datasets[i]["measure"] not in ("asking_price", "retail_price"):
            E.append(f"$.economics: {i} n'est pas un prix affiche")
    for i in ec["realized_sale_dataset_ids"]:
        if i in datasets and datasets[i]["measure"] != "sold_price":
            E.append(f"$.economics: {i} n'est pas un prix de vente realisee")
    for lab, ids in (("availability", ec["availability"]["evidence_claim_ids"]), ("fees", ec["fees"]["claim_ids"]),
                     ("liquidity", ec["liquidity"]["claim_ids"]), ("supply_demand", ec["supply_demand_claim_ids"])):
        ref(ids, claims, f"$.economics.{lab}")
    if ec["availability"]["buyable_verified"]:
        ev = [claims[i] for i in ec["availability"]["evidence_claim_ids"] if i in claims]
        if not any(c["verification"] == "verified" for c in ev):
            E.append("$.economics.availability: achetabilite verifiee sans fait verifie")
    if ec["fees"]["verified"]:
        if not any(claims[i]["verification"] == "verified" for i in ec["fees"]["claim_ids"] if i in claims):
            E.append("$.economics.fees: frais declares verifies sans fait verifie")
    for h in ec["roi_hypotheses"]:
        ref(h["assumption_claim_ids"], claims, f"$.economics.roi_hypotheses[{h['scenario']}]")

    # --- decisions (politique EDGE)
    op, ed = r["decisions"]["agent_opinion"], r["decisions"]["edge_decision"]
    if op:
        ref(op["claim_ids"], claims, "$.decisions.agent_opinion")
    if ed["decided_by"] == "none" and ed["decision"] != "NOT_EVALUATED":
        E.append("$.decisions.edge_decision: decision sans moteur EDGE (seul NOT_EVALUATED est permis)")
    if ed["decided_by"] == "edge_engine" and not ed.get("decided_at"):
        E.append("$.decisions.edge_decision: decided_at requis pour une decision du moteur")
    if ed["decision"] in POSITIVE:
        if ed["decided_by"] != "edge_engine" or not ed["evidence_refs"] or not ed["rules_applied"]:
            E.append("$.decisions.edge_decision: BUY/STRONG_BUY exige le moteur EDGE, ses regles et ses preuves")
        if not ec["availability"]["buyable_verified"]:
            E.append("$.decisions.edge_decision: BUY/STRONG_BUY incompatible avec une achetabilite non verifiee")
        if not ec["realized_sale_dataset_ids"]:
            E.append("$.decisions.edge_decision: BUY/STRONG_BUY sans ventes realisees")
        if r["simulated"]:
            E.append("$.decisions.edge_decision: BUY/STRONG_BUY impossible dans un rapport simule")

    # --- simulation
    any_sim = (any(s["simulated"] for s in r["sources"]) or any(d["simulated"] for d in r["datasets"])
               or any(c["verification"] == "simulated" for c in r["claims"]))
    if any_sim and not r["simulated"]:
        E.append("$.simulated: le rapport contient des elements simules mais se declare reel")

    # --- statut
    st = r["production_status"]
    facts = [c for c in r["claims"] if c["kind"] == "fact"]
    if st == "complete":
        if r["simulated"]:
            E.append("$.production_status: 'complete' interdit pour un rapport simule")
        if not r["sources"]:
            E.append("$.production_status: 'complete' sans aucune source")
        if any(c["verification"] != "verified" for c in facts):
            E.append("$.production_status: 'complete' avec des faits non verifies (utiliser 'partial')")
        if ed["decided_by"] != "edge_engine":
            E.append("$.production_status: 'complete' sans decision du moteur EDGE")
    if st == "retracted" and not r["history"]["conclusion_changes"]:
        E.append("$.production_status: retrait sans conclusion_changes motive")

    # --- versionnement
    h, sup = r["history"], r.get("supersedes")
    if r["report_version"] == 1:
        if sup is not None or h["previous_versions"]:
            E.append("$.report_version: v1 ne peut rien remplacer")
    else:
        if not sup:
            E.append("$.supersedes: obligatoire pour une version > 1")
        else:
            if sup["report_id"] != r["report_id"] or sup["report_version"] != r["report_version"] - 1:
                E.append("$.supersedes: doit designer la version immediatement precedente du meme rapport")
            if not any(pv["report_version"] == sup["report_version"] and pv["content_sha256"] == sup["content_sha256"]
                       for pv in h["previous_versions"]):
                E.append("$.history.previous_versions: version remplacee absente ou empreinte differente")
        if not h["changes"] and not h["corrections"]:
            E.append("$.history: une nouvelle version doit motiver ses changements ou corrections")

    # --- fraicheur (avertissement)
    max_age = (r.get("freshness") or {}).get("max_data_age_days")
    if max_age is not None and created and as_of and created - as_of > timedelta(days=max_age):
        W.append(f"donnees anterieures de plus de {max_age} j a la redaction (perimees)")
    return E, W


# ------------------------------------------------------------ evaluation

LABELS = {
    "invalid": "RAPPORT INVALIDE — ne pas afficher comme analyse",
    "retracted": "RAPPORT RETIRE",
    "simulated": "DONNEES SIMULEES — exemple, aucune valeur reelle",
    "draft": "BROUILLON — non verifie",
    "partially_verified": "PARTIELLEMENT VERIFIE — elements non verifies ou verification non documentee",
    # Fiabilite a la redaction seulement : coherence des references controlee
    # et verification DECLAREE par des humains/collecteurs identifies. Ce n'est
    # pas une garantie de verite ni d'actualite (voir timeliness).
    "fully_verified": "VERIFICATION DOCUMENTEE — faits sources et verifies par des verificateurs declares",
}


def timeliness(report, now=None, default_max_days=DEFAULT_MAX_DATA_AGE_DAYS):
    """Actualite des donnees A LA DATE DE CONSULTATION (distincte de la
    fiabilite). current | stale | unknown. Sans politique declaree : politique
    prudente par defaut."""
    now = now or datetime.now(timezone.utc)
    declared = (report.get("freshness") or {}).get("max_data_age_days")
    max_days = declared if isinstance(declared, int) and not isinstance(declared, bool) else default_max_days
    out = {"evaluated_at": now.isoformat(), "max_age_days": max_days,
           "policy": "declared" if max_days == declared else "default",
           "data_as_of": report.get("data_as_of"), "data_age_days": None, "status": "unknown"}
    try:
        as_of = _dt(report["data_as_of"])
    except (KeyError, ValueError, TypeError):
        return out
    age = now - as_of
    out["data_age_days"] = round(age.total_seconds() / 86400, 2)
    if age < timedelta(0):
        return out  # consultation anterieure aux donnees : incoherent -> inconnu
    out["status"] = "current" if age <= timedelta(days=max_days) else "stale"
    return out


def assess(report, now=None):
    """Retourne {valid, errors, warnings, verification_level, label,
    timeliness, display_label}.
    - verification_level : FIABILITE a la redaction, calculee (jamais declaree),
      independante de la date de consultation.
    - timeliness : ACTUALITE a la date `now` (consultation).
    - display_label : ce qu'une interface doit afficher (fiabilite + actualite)."""
    if not isinstance(report, dict) or report.get("schema") != SCHEMA_ID:
        return {"valid": False, "errors": ["$.schema: rapport EDGE Intelligence attendu"], "warnings": [],
                "verification_level": "invalid", "label": LABELS["invalid"],
                "timeliness": {"status": "unknown"}, "display_label": LABELS["invalid"]}
    errors = check_schema(report, SCHEMA)
    warnings = []
    if not errors:
        try:
            canonical_json(report)
        except ValueError:
            errors.append("$: nombre non fini (NaN/Infinity) non serialisable")
        e2, warnings = check_semantics(report)
        errors += e2
    if errors:
        level = "invalid"
    elif report["production_status"] == "retracted":
        level = "retracted"
    elif report["simulated"]:
        level = "simulated"
    elif report["production_status"] == "draft":
        level = "draft"
    elif report["production_status"] == "complete" and not warnings and not any(
            (c["verification"] == "contradicted" or c.get("contradicting_source_ids"))
            and c["kind"] != "invalidated" for c in report["claims"]):
        level = "fully_verified"
    else:
        level = "partially_verified"
    t = timeliness(report, now)
    display = LABELS[level]
    if level not in ("invalid", "retracted"):
        if t["status"] == "stale":
            display += (f" — DONNEES PERIMEES ({t['data_age_days']:.0f} j > {t['max_age_days']} j, "
                        f"politique {'declaree' if t['policy'] == 'declared' else 'par defaut'}) : "
                        "ne pas considerer comme actuel")
        elif t["status"] == "unknown":
            display += " — ACTUALITE INCONNUE"
    return {"valid": not errors, "errors": errors, "warnings": warnings,
            "verification_level": level, "label": LABELS[level],
            "timeliness": t, "display_label": display}
