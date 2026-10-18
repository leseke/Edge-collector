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

ALLOWED_STATES = {"CANDIDATE", "REJECTED", "NO_DATA"}
REQUIRED = ("source", "source_url", "observed_at", "name", "price_eur")


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
    missing = [key for key in REQUIRED if observation.get(key) in (None, "")]
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
        price = float(observation["price_eur"])
        if price <= 0 or price == float("inf") or price != price:
            raise ValueError("Non-positive or non-finite price")
    except (TypeError, ValueError, OverflowError):
        return None, "invalid:date_or_price"
    source = str(observation["source"]).strip()
    name = str(observation["name"]).strip()
    if not source or not name:
        return None, "invalid:source_or_name"
    return {
        "id": _candidate_id(source, observation["external_id"]),
        "name": name,
        "source": source,
        "external_id": str(observation["external_id"]),
        "source_url": observation["source_url"],
        "observed_at": observed.isoformat(),
        "price_eur": round(price, 2),
        "status": "CANDIDATE",
        "allocation_eur": [0, 0],
        "decision": "NO_DATA",
        "evidence_type": "ASKING_PRICE",
    }, None


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
    return {
        "schema_version": 1,
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
        "investment_decision": "CASH",
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
