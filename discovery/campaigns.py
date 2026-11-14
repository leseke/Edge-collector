"""Campagnes de prospection : execution, budget, journal, expansion.

Une campagne n'emet jamais de recommandation : elle produit des
observations normalisees, des candidats et un journal d'execution.
"""
import json
import re
import time
from collections import Counter
from datetime import datetime, timezone

from discovery.adapters import SourceUnavailable
from investigation.spend import SpendNotAuthorized
from discovery.engine import process
from discovery.identity import fold, lego_set_numbers
from edge_io import redact

FAMILIES = {
    "price_anomaly": "Anomalies de prix",
    "emerging": "Produits emergents",
    "rarity": "Rarete et objets de collection",
    "end_of_life": "Fins de production et ruptures",
    "liquidity": "Ventes conclues et liquidite",
    "catalyst": "Changements culturels et evenements futurs",
    "revalidation": "Revalidation des opportunites precedentes",
}

_STOP = set("""lego set neuf new sealed scelle boite box avec sans pour the and
de la le les des du un une en edition officiel original pokemon one piece
coffret display booster""".split())


def validate_campaign(c):
    errors = []
    if not isinstance(c.get("id"), str) or not re.fullmatch(r"[a-z0-9_\-]{3,64}", c.get("id", "")):
        errors.append("id")
    if c.get("family") not in FAMILIES:
        errors.append("family")
    if not c.get("queries") or not all(isinstance(q, str) and q.strip() for q in c["queries"]):
        errors.append("queries")
    if not c.get("sources"):
        errors.append("sources")
    for k in ("max_calls", "max_expansions", "limit_per_query"):
        if k in c and (not isinstance(c[k], int) or c[k] < 0):
            errors.append(k)
    return errors


def load_campaigns(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["campaigns"]


def _expansion_queries(observations, base_queries, already, max_n):
    """Nouvelles pistes issues des resultats : references precises
    decouvertes (pour aller chercher leurs ventes conclues), puis
    termes recurrents (sous-themes)."""
    out = []
    keys = Counter()
    for o in observations:
        for n in lego_set_numbers(o.get("name", "")):
            keys[n] += 1
    for num, _ in keys.most_common():
        q = f"LEGO {num}"
        if q not in already and q not in out:
            out.append(q)
    base_tokens = set(fold(" ".join(base_queries)).split())
    toks = Counter()
    for o in observations:
        words = set(re.findall(r"[a-z]{4,}", fold(o.get("name", ""))))
        toks.update(w for w in words if w not in _STOP and w not in base_tokens)
    for w, n in toks.most_common(5):
        if n < 3:
            break
        q = f"{base_queries[0]} {w}"
        if q not in already and q not in out:
            out.append(q)
    return out[:max_n]


def run_campaign(campaign, adapters, now=None, clock=time.monotonic):
    """Execute une campagne. adapters : {nom_source: adaptateur}.

    Retourne {run, observations, discovery} ; run contient le journal
    complet (chaque appel : statut, duree, erreurs, cout)."""
    errors = validate_campaign(campaign)
    started = now or datetime.now(timezone.utc).isoformat()
    run = {
        "campaign_id": campaign.get("id"), "family": campaign.get("family"),
        "started_at": started, "calls": [], "expansions": [],
        "cost_units": 0, "status": None, "config_errors": errors,
    }
    if errors:
        run["status"] = "INVALID_CONFIG"
        return {"run": run, "observations": [], "discovery": None}

    max_calls = campaign.get("max_calls", 10)
    limit = campaign.get("limit_per_query", 20)
    queue = [(q, s, 0) for q in campaign["queries"] for s in campaign["sources"]]
    done_queries = set(campaign["queries"])
    observations = []
    expanded = False

    while queue:
        query, source, depth = queue.pop(0)
        call = {"query": query, "source": source, "depth": depth}
        n_exec = sum(1 for c in run["calls"] if c["status"] in ("OK", "EMPTY", "ERROR"))
        if n_exec >= max_calls:
            call["status"] = "SKIPPED_BUDGET"
            run["calls"].append(call)
            continue
        adapter = adapters.get(source)
        if adapter is None:
            call["status"] = "SKIPPED_UNAVAILABLE"
            call["error"] = "adaptateur non configure"
            run["calls"].append(call)
            continue
        if getattr(adapter, "paid", False) and not hasattr(adapter, "guard") \
                and getattr(adapter, "spend_guard", None) is None:
            # Source payante sans garde de depense : jamais appelee. Aucun
            # champ de campagne (ex. "paid_authorized") ne peut l'autoriser.
            call["status"] = "SKIPPED_PAID_NOT_AUTHORIZED"
            call["error"] = "source payante sans garde de depense"
            run["calls"].append(call)
            continue
        t0 = clock()
        try:
            obs = adapter.search(query, limit)
            call["status"] = "OK" if obs else "EMPTY"
            call["n_observations"] = len(obs)
            for o in obs:
                o.setdefault("query", query)
            observations.extend(obs)
            run["cost_units"] += getattr(adapter, "cost_per_call", 1)
        except SpendNotAuthorized as e:
            call["status"] = "SKIPPED_PAID_NOT_AUTHORIZED"
            call["error"] = redact(e)
        except SourceUnavailable as e:
            call["status"] = "SKIPPED_UNAVAILABLE"
            call["error"] = redact(e)
        except Exception as e:  # echec technique : jamais silencieux
            call["status"] = "ERROR"
            call["error"] = f"{type(e).__name__}: {redact(e)}"
            run["cost_units"] += getattr(adapter, "cost_per_call", 1)
        call["duration_s"] = round(clock() - t0, 3)
        run["calls"].append(call)

        if not queue and not expanded and campaign.get("max_expansions", 0) > 0:
            expanded = True
            new_q = _expansion_queries(observations, campaign["queries"], done_queries,
                                       campaign["max_expansions"])
            exp_sources = campaign.get("expansion_sources", campaign["sources"])
            for q in new_q:
                done_queries.add(q)
                # une source specialisee ne recoit que les requetes qu'elle
                # declare savoir traiter (ex. numero de set pour BrickLink)
                targets = [s for s in exp_sources
                           if s not in adapters or getattr(adapters[s], "accepts", lambda _q: True)(q)]
                if targets:
                    run["expansions"].append(q)
                    queue.extend((q, s, 1) for s in targets)

    statuses = [c["status"] for c in run["calls"]]
    executed = [s for s in statuses if s in ("OK", "EMPTY", "ERROR")]
    ok = [s for s in statuses if s in ("OK", "EMPTY")]
    if not executed or not ok:
        run["status"] = "FAILED"
    elif len(ok) < len(statuses):
        run["status"] = "PARTIAL"
    elif not observations:
        run["status"] = "NO_DATA"
    else:
        run["status"] = "COMPLETED"
    run["n_calls_executed"] = len(executed)
    run["n_errors"] = statuses.count("ERROR")
    run["n_observations"] = len(observations)
    run["simulated"] = any(o.get("simulated") for o in observations)
    run["finished_at"] = datetime.now(timezone.utc).isoformat()
    discovery = process(observations, campaign["id"], generated_at=run["finished_at"])
    return {"run": run, "observations": observations, "discovery": discovery}
