"""EDGE — moteur de decision (V4).

Separation stricte :
  decision economique (independante du capital)
  -> opportunity_alert
  -> financement (capital_sufficient / allocation_sufficient)
  -> execution_ready (financement + conditions d'execution + config valide)

Les donnees financieres privees (treasury, engaged, montants d'allocation)
ne sortent JAMAIS de ce module vers radar.json / GitHub Pages / Telegram :
utiliser public_product_view() et build_public_summary().
"""
import json
import math
import os

SIGNAL_DECISIONS = ("BUY", "STRONG_BUY")
ECONOMIC_DECISIONS = ("STRONG_BUY", "BUY", "WAIT", "WATCH")
FAILURE_DECISIONS = ("NO_DATA", "ERROR")
ALL_PRODUCT_DECISIONS = ECONOMIC_DECISIONS + FAILURE_DECISIONS

# Cles financieres privees : jamais publiees.
PRIVATE_KEYS = {
    "treasury", "engaged", "capital_engaged", "capital_monthly",
    "capital_max_available", "capital_available",
}
# Politique publiable (pourcentages, pas de montants).
PUBLIC_POLICY_KEYS = (
    "max_position_pct", "allocation_buy_pct",
    "allocation_progressive_pct", "allocation_future_classic_pct",
    "min_coverage_for_cash", "enabled_sources",
)

DEFAULT_CONFIG = {
    "capital_monthly": 300,
    "capital_max_available": 600,
    "capital_engaged": 0,
    "max_position_pct": 40,
    "allocation_buy_pct": [15, 40],
    "allocation_progressive_pct": [5, 20],
    "allocation_future_classic_pct": [5, 15],
}

# Couverture minimale (part des produits avec donnees exploitables)
# pour qu'une absence de signal puisse etre conclue en CASH.
DEFAULT_MIN_COVERAGE_FOR_CASH = 1.0


# ---------------------------------------------------------------- config

def load_config(path="config.json", private_path="config.private.json"):
    """Charge la configuration publique puis la surcharge privee.

    config.private.json (gitignore) ou les variables d'environnement
    EDGE_TREASURY / EDGE_ENGAGED portent les montants reels.
    """
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = dict(DEFAULT_CONFIG)
    # Une autorisation de depense n'est valable que dans la config PRIVEE.
    if "paid_investigation" in config:
        config.pop("paid_investigation")
        config.setdefault("_config_warnings", []).append(
            "paid_investigation ignore dans config.json public (seul config.private.json fait foi)")
    if private_path and os.path.exists(private_path):
        with open(private_path, "r", encoding="utf-8") as f:
            config.update(json.load(f))
    for env, key in (("EDGE_TREASURY", "treasury"), ("EDGE_ENGAGED", "engaged")):
        raw = os.environ.get(env)
        if raw not in (None, ""):
            try:
                config[key] = float(raw)
            except ValueError:
                config.setdefault("_config_errors", []).append(f"{env}:not_a_number")
    return config


def load_portfolio(path="portfolio.json"):
    """Charge les positions reelles de l'utilisateur."""
    if not os.path.exists(path):
        return {"positions": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _finite_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _valid_pct_range(v):
    return (isinstance(v, (list, tuple)) and len(v) == 2
            and all(_finite_number(x) for x in v)
            and 0 <= v[0] <= v[1] <= 100)


def validate_config(config):
    """Retourne la liste des erreurs de configuration (vide = valide).

    Une configuration invalide n'autorise JAMAIS une execution.
    """
    errors = list(config.get("_config_errors", []))
    for key in ("allocation_buy_pct", "allocation_progressive_pct",
                "allocation_future_classic_pct"):
        if key in config and not _valid_pct_range(config[key]):
            errors.append(f"{key}:invalid_range")
    if "max_position_pct" in config:
        v = config["max_position_pct"]
        if not _finite_number(v) or not 0 < v <= 100:
            errors.append("max_position_pct:invalid")
    for key in ("treasury", "engaged", "capital_engaged"):
        if key in config and config[key] is not None:
            v = config[key]
            if not _finite_number(v) or v < 0:
                errors.append(f"{key}:invalid")
    if "min_coverage_for_cash" in config:
        v = config["min_coverage_for_cash"]
        if not _finite_number(v) or not 0 < v <= 1:
            errors.append("min_coverage_for_cash:invalid")
    return errors


def capital_state(config):
    """Etat du capital. treasury = tresorerie totale AVANT engagements.

    capital_available = max(0, treasury - engaged).
    Si treasury est inconnu, capital_available vaut None : on ne conclut
    jamais qu'une execution est possible.
    """
    errors = validate_config(config)
    treasury = config.get("treasury")
    engaged = config.get("engaged", config.get("capital_engaged", 0))
    known = _finite_number(treasury) and _finite_number(engaged) and not errors
    available = max(0.0, float(treasury) - float(engaged)) if known else None
    return {
        "treasury": treasury if known else None,
        "engaged": engaged if known else None,
        "capital_available": available,
        "capital_known": known,
        "config_valid": not errors,
        "config_errors": errors,
    }


def compute_capital_available(config):
    """Compatibilite : capital disponible (0 si inconnu)."""
    return capital_state(config)["capital_available"] or 0


def compute_allocation_frange(config, signal_type):
    """Fourchette d'allocation EUR (privee). (0, 0) si capital inconnu.

    signal_type : 'BUY', 'STRONG_BUY', 'PROGRESSIVE', 'FUTURE_CLASSIC'
    """
    state = capital_state(config)
    if not state["capital_known"]:
        return (0, 0)
    available = state["capital_available"]
    if signal_type in ("BUY", "STRONG_BUY"):
        pct_lo, pct_hi = config.get("allocation_buy_pct", [15, 40])
    elif signal_type == "PROGRESSIVE":
        pct_lo, pct_hi = config.get("allocation_progressive_pct", [5, 20])
    elif signal_type == "FUTURE_CLASSIC":
        pct_lo, pct_hi = config.get("allocation_future_classic_pct", [5, 15])
    else:
        return (0, 0)
    pct_hi = min(pct_hi, config.get("max_position_pct", 40))
    pct_lo = min(pct_lo, pct_hi)
    return (round(available * pct_lo / 100), round(available * pct_hi / 100))


def estimate_cycle(median_price, target_buy, n_sales_30d):
    """Estime le stade du cycle (1 a 7) — heuristique inchangee depuis V3."""
    if target_buy is None or median_price is None:
        return (0, "Inconnu")
    ratio = median_price / target_buy
    if ratio < 0.85:
        if n_sales_30d is None or n_sales_30d < 5:
            return (1, "Invisibilite")
        return (2, "Signal")
    elif ratio < 1.0:
        return (2, "Signal")
    elif ratio < 1.10:
        return (3, "Acceleration")
    elif ratio < 1.25:
        return (4, "Mainstream")
    elif ratio < 1.50:
        return (5, "FOMO")
    elif ratio < 1.75:
        return (6, "Saturation")
    return (7, "Capitulation")


# ---------------------------------------------------------------- decision

def economic_decision(item, prix_eur):
    """Decision economique pure : ne lit AUCUNE donnee de capital."""
    target = item.get("target_buy")
    strong = item.get("target_strong_buy")
    if not _finite_number(prix_eur) or prix_eur <= 0:
        return "NO_DATA", "Prix inexploitable"
    if strong and prix_eur <= strong:
        return "STRONG_BUY", f"ACHAT FORT : {prix_eur:.0f} EUR <= {strong} EUR"
    if target and prix_eur <= target:
        return "BUY", f"ACHAT : {prix_eur:.0f} EUR <= {target} EUR"
    if target:
        ecart = (prix_eur - target) / target * 100
        return "WAIT", f"Attendre : {prix_eur:.0f} EUR > {target} EUR (ecart {ecart:+.0f} %)"
    return "WATCH", f"Surveiller : {prix_eur:.0f} EUR, pas de cible definie"


def funding_status(decision, category, execution_price, config, offer_verified=False):
    """Statut de financement, separe de la decision economique."""
    state = capital_state(config)
    signal = decision in SIGNAL_DECISIONS
    alloc_type = "BUY" if signal else ("FUTURE_CLASSIC" if category == "FUTURE_CLASSIC" else None)
    alloc = compute_allocation_frange(config, alloc_type) if (alloc_type and signal) else (0, 0)
    price_ok = _finite_number(execution_price) and execution_price > 0
    if state["capital_known"] and price_ok:
        capital_sufficient = state["capital_available"] >= execution_price
        allocation_sufficient = alloc[1] >= execution_price if signal else False
    else:
        capital_sufficient = None
        allocation_sufficient = None
    blockers = []
    if not state["config_valid"]:
        blockers.append("config_invalid")
    if not state["capital_known"]:
        blockers.append("capital_unknown")
    if not signal:
        blockers.append("no_economic_signal")
    if not price_ok:
        blockers.append("execution_price_unknown")
    if not offer_verified:
        blockers.append("no_verified_offer")
    if capital_sufficient is False:
        blockers.append("capital_insufficient")
    if allocation_sufficient is False and signal:
        blockers.append("allocation_insufficient")
    execution_ready = (signal and state["config_valid"] and offer_verified
                       and capital_sufficient is True and allocation_sufficient is True)
    return {
        "capital_sufficient": capital_sufficient,
        "allocation_sufficient": allocation_sufficient,
        "execution_ready": bool(execution_ready),
        "execution_blockers": [] if execution_ready else blockers,
        "allocation_eur": list(alloc) if signal else [0, 0],
    }


def decide(item, prix_eur, snap, config, offer=None):
    """Decision complete pour un produit de la watchlist.

    offer : offre achetable verifiee {price_eur, url, seller} ou None.
    Le capital n'influence JAMAIS decision ni opportunity_alert.
    """
    category = item.get("category", "flip").upper()
    niveau, message = economic_decision(item, prix_eur)
    target = item.get("target_buy")
    snap = snap or {}
    n_sales = snap.get("sold_count_30d") or snap.get("_n_matched") or 0
    cycle_num, cycle_label = estimate_cycle(snap.get("sold_price_median"), target, n_sales)
    ecart_pct = round((prix_eur - target) / target * 100, 1) if (target and _finite_number(prix_eur)) else None

    offer_price = offer.get("price_eur") if offer else None
    exec_price = offer_price if _finite_number(offer_price) else prix_eur
    funding = funding_status(niveau, category, exec_price, config,
                             offer_verified=_finite_number(offer_price))
    return {
        "decision": niveau,
        "message": message,
        "opportunity_alert": niveau in SIGNAL_DECISIONS,
        "allocation_eur": funding["allocation_eur"],
        "capital_sufficient": funding["capital_sufficient"],
        "allocation_sufficient": funding["allocation_sufficient"],
        "execution_ready": funding["execution_ready"],
        "execution_blockers": funding["execution_blockers"],
        "cycle_num": cycle_num,
        "cycle_label": cycle_label,
        "categorie": category,
        "ecart_pct": ecart_pct,
    }


# ---------------------------------------------------------------- synthese

class InconsistentCounters(ValueError):
    pass


def summarize(products, config, sources_failed=None):
    """Statut global coherent. Ne confond jamais absence de signal et
    absence de donnees ; CASH seulement si couverture suffisante.
    """
    counts = {d: 0 for d in ALL_PRODUCT_DECISIONS}
    for p in products:
        d = p.get("decision")
        if d not in counts:
            raise InconsistentCounters(f"decision inconnue : {d!r}")
        counts[d] += 1
    total = len(products)
    n_buy = counts["BUY"] + counts["STRONG_BUY"]
    n_failed = counts["NO_DATA"] + counts["ERROR"]
    if n_buy + counts["WAIT"] + counts["WATCH"] + n_failed != total:
        raise InconsistentCounters("compteurs incoherents")
    n_ok = total - n_failed
    coverage = (n_ok / total) if total else 0.0
    min_cov = config.get("min_coverage_for_cash", DEFAULT_MIN_COVERAGE_FOR_CASH)
    config_errors = validate_config(config)

    if total == 0:
        data_status = "NO_DATA"
    elif n_ok == 0:
        data_status = "FAILED"
    elif n_failed > 0 or sources_failed:
        data_status = "PARTIAL"
    else:
        data_status = "OK"

    if n_buy > 0:
        decision = f"{n_buy} SIGNAL"
        posture = "SIGNALS"
    elif data_status in ("NO_DATA", "FAILED"):
        decision = data_status
        posture = "NO_CONCLUSION"
    elif coverage < min_cov:
        decision = "PARTIAL"
        posture = "NO_CONCLUSION"
    else:
        decision = "CASH"
        posture = "CASH"

    return {
        "schema_version": 4,
        "n_buy": n_buy,
        "n_strong_buy": counts["STRONG_BUY"],
        "n_wait": counts["WAIT"],
        "n_watch": counts["WATCH"],
        "n_nodata": n_failed,
        "n_error": counts["ERROR"],
        "total": total,
        "coverage": round(coverage, 3),
        "min_coverage_for_cash": min_cov,
        "data_status": data_status,
        "posture": posture,
        "decision": decision,
        "n_opportunity_alert": sum(1 for p in products if p.get("opportunity_alert")),
        "n_execution_ready": sum(1 for p in products if p.get("execution_ready")),
        "config_valid": not config_errors,
        "sources_failed": sorted(sources_failed or []),
    }


def public_summary(summary):
    return {k: v for k, v in summary.items() if k not in PRIVATE_PRODUCT_KEYS}


def public_policy(config):
    return {k: config[k] for k in PUBLIC_POLICY_KEYS if k in config}


PRIVATE_PRODUCT_KEYS = {"allocation_eur", "capital_sufficient",
                        "allocation_sufficient", "execution_blockers",
                        "execution_ready", "n_execution_ready"}


def public_product_view(product):
    """Vue publiable : retire les montants et indicateurs derives du capital.

    Meme les booleens de financement restent prives : ils permettraient
    d'encadrer le capital reel par recoupement des prix publies.
    """
    return {k: v for k, v in product.items() if k not in PRIVATE_PRODUCT_KEYS}


def assert_no_private_leak(obj, path="$"):
    """Leve ValueError si une cle financiere privee apparait."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in PRIVATE_KEYS or k in PRIVATE_PRODUCT_KEYS:
                raise ValueError(f"fuite de donnee privee : {path}.{k}")
            assert_no_private_leak(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            assert_no_private_leak(v, f"{path}[{i}]")
