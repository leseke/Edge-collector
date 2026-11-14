"""Fail-closed discovery candidate normalization.

This module does not scrape marketplaces or decide BUY. It accepts observations
from future authorized collectors and produces auditable candidates.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from discovery.identity import condition_of, identify

ALLOWED_STATES = {"CANDIDATE", "REJECTED", "NO_DATA"}
REQUIRED = ("source", "source_url", "observed_at", "name", "price_eur")

# Nature de la preuve. Chaque type a une valeur probante differente :
EVIDENCE_TYPES = {
    "ASKING_PRICE",     # annonce active (prix demande, pas une vente)
    "RETAIL_OFFER",     # offre boutique achetable (prix public)
    "SOLD",             # vente individuelle confirmee
    "SOLD_AGGREGATE",   # statistiques agregees de ventes (ex. BrickLink 6 mois)
    "MARKET_TREND",     # prix de marche indicatif (ex. trend Cardmarket)
    "AVAILABILITY",     # disponibilite commerciale (ex. Brickset : dates, prix boutique)
    "CULTURAL_SIGNAL",  # signal culturel (Trends, Reddit...) : jamais une valorisation
}
SALE_EVIDENCE = {"SOLD"}
AGGREGATE_EVIDENCE = {"SOLD_AGGREGATE"}
BUYABLE_EVIDENCE = {"ASKING_PRICE", "RETAIL_OFFER"}
UNPRICED_EVIDENCE = {"AVAILABILITY", "CULTURAL_SIGNAL"}


def _num(v, minimum=0.0, integer=False):
    if isinstance(v, bool):
        raise ValueError("bool")
    f = float(v)
    if f != f or f in (float("inf"), float("-inf")) or f < minimum:
        raise ValueError("range")
    if integer and f != int(f):
        raise ValueError("int")
    return int(f) if integer else round(f, 2)


def _validate_aggregate(a):
    """Statistiques agregees : periode, quantites et prix explicites.
    Aucune valeur manquante n'est completee."""
    if not isinstance(a, dict):
        raise ValueError("aggregate")
    out = {
        "period_days": _num(a["period_days"], 1, True),
        "total_quantity": _num(a["total_quantity"], 0, True),
        "lots": _num(a["lots"], 0, True),
        "avg_price_eur": _num(a["avg_price_eur"], 0.01),
        "qty_avg_price_eur": _num(a["qty_avg_price_eur"], 0.01),
        "min_price_eur": _num(a["min_price_eur"], 0.01),
        "max_price_eur": _num(a["max_price_eur"], 0.01),
        "condition": str(a.get("condition", "")).upper(),
        "region": a.get("region"),
        "guide": a.get("guide", "sold"),
    }
    if not out["min_price_eur"] <= min(out["avg_price_eur"], out["qty_avg_price_eur"]) \
            <= max(out["avg_price_eur"], out["qty_avg_price_eur"]) <= out["max_price_eur"]:
        raise ValueError("incoherent prices")
    if out["lots"] > out["total_quantity"]:
        raise ValueError("lots > quantity")
    return out


def _validate_availability(a):
    if not isinstance(a, dict):
        raise ValueError("availability")
    from datetime import date as _d
    out = {"region": a.get("region"), "retail_price_eur": None,
           "date_first": None, "date_last": None}
    if a.get("retail_price_eur") not in (None, ""):
        out["retail_price_eur"] = _num(a["retail_price_eur"], 0.01)
    for k in ("date_first", "date_last"):
        if a.get(k):
            out[k] = _d.fromisoformat(str(a[k])[:10]).isoformat()
    return out


def _valid_url(value):
    try:
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username and not parsed.password
    except (TypeError, ValueError):
        return False


def _candidate_id(source, external_id):
    value = f"{source.strip().lower()}:{str(external_id).strip().lower()}"
    return "cand_" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def normalize(observation):
    """Normalize one source observation without inventing financial data."""
    evidence_type = observation.get("evidence_type", "ASKING_PRICE")
    if evidence_type not in EVIDENCE_TYPES:
        return None, "invalid:evidence_type"
    required = [k for k in REQUIRED if not (k == "price_eur" and evidence_type in UNPRICED_EVIDENCE)]
    missing = [key for key in required if observation.get(key) in (None, "")]
    if missing:
        return None, "missing:" + ",".join(missing)
    if not observation.get("external_id"):
        return None, "missing:external_id"
    if not _valid_url(observation["source_url"]):
        return None, "invalid:source_url"
    try:
        observed = datetime.fromisoformat(str(observation["observed_at"]).replace("Z", "+00:00"))
        if observed.tzinfo is None:
            raise ValueError("Timezone required")
        price = None
        if observation.get("price_eur") not in (None, ""):
            price = float(observation["price_eur"])
            if price <= 0 or price == float("inf") or price != price:
                raise ValueError("Non-positive or non-finite price")
    except (TypeError, ValueError, OverflowError):
        return None, "invalid:date_or_price"
    extra = {}
    try:
        if evidence_type == "SOLD_AGGREGATE":
            extra["aggregate"] = _validate_aggregate(observation.get("aggregate"))
            if extra["aggregate"]["condition"] != "NEW":
                return None, "rejected:used_condition"
        elif evidence_type == "AVAILABILITY":
            extra["availability"] = _validate_availability(observation.get("availability"))
        elif evidence_type == "CULTURAL_SIGNAL":
            sig = observation.get("signal")
            if not isinstance(sig, dict) or not sig.get("metric"):
                raise ValueError("signal")
            extra["signal"] = {"metric": str(sig["metric"]), "value": sig.get("value")}
    except (KeyError, TypeError, ValueError):
        return None, f"invalid:{evidence_type.lower()}"
    source = str(observation["source"]).strip()
    name = str(observation["name"]).strip()
    if not source or not name:
        return None, "invalid:source_or_name"
    currency = str(observation.get("currency_src", "EUR")).upper()
    if currency != "EUR" and observation.get("fx_rate") in (None, ""):
        # Pas de conversion implicite : une devise sans taux est refusee.
        return None, "invalid:currency_without_fx"
    product_key, id_conf, id_notes = identify(name, observation.get("product_key"))
    if product_key is None:
        return None, "rejected:identity"
    condition = condition_of(name, observation.get("condition"))
    if condition == "USED":
        return None, "rejected:used_condition"
    return {
        "id": _candidate_id(source, observation["external_id"]),
        "name": name,
        "source": source,
        "external_id": str(observation["external_id"]),
        "source_url": observation["source_url"],
        "observed_at": observed.isoformat(),
        "price_eur": round(price, 2) if price is not None else None,
        "status": "CANDIDATE",
        "allocation_eur": [0, 0],
        "decision": "NO_DATA",
        "evidence_type": evidence_type,
        "product_key": product_key,
        "identity_confidence": id_conf,
        "identity_notes": id_notes,
        "condition": condition,
        "shipping_eur": _opt_money(observation.get("shipping_eur")),
        "seller": observation.get("seller"),
        "seller_type": observation.get("seller_type", "UNKNOWN"),
        "market": observation.get("market"),
        "query": observation.get("query"),
        "currency_src": currency,
        "simulated": bool(observation.get("simulated")),
        **extra,
    }, None


def _opt_money(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return round(f, 2) if f >= 0 and f == f and f != float("inf") else None


def process(observations, campaign_id, generated_at=None):
    if not isinstance(observations, list):
        raise ValueError("observations must be a list")
    if not isinstance(campaign_id, str) or not campaign_id.strip():
        raise ValueError("campaign_id required")
    candidates, rejected, seen = [], [], set()
    for index, obs in enumerate(observations):
        if not isinstance(obs, dict):
            rejected.append({"index": index, "reason": "invalid:record"})
            continue
        candidate, error = normalize(obs)
        if error:
            rejected.append({"index": index, "reason": error})
        elif candidate["id"] not in seen:
            seen.add(candidate["id"])
            candidates.append(candidate)
    status = "CANDIDATES" if candidates else ("NO_DATA" if not observations else "ALL_REJECTED")
    return {
        "schema_version": 2,
        "status": status,
        "campaign_id": campaign_id,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "summary": {
            "observations": len(observations),
            "candidates": len(candidates),
            "rejected": len(rejected),
            "duplicates": len(observations) - len(candidates) - len(rejected),
        },
        "candidates": candidates,
        "rejected": rejected,
        # Un candidat n'est pas une decision. "CASH" n'est jamais emis ici :
        # la posture CASH exige une couverture suffisante (cf. edge_engine).
        "investment_decision": "NOT_EVALUATED",
        "allocation_eur": 0,
    }


def run_file(input_path, output_path, campaign_id):
    observations = json.loads(Path(input_path).read_text(encoding="utf-8"))
    result = process(observations, campaign_id)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--campaign", required=True)
    args = parser.parse_args()
    run_file(args.input, args.output, args.campaign)
