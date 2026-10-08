import json
import os
from datetime import datetime


def load_config(path="config.json"):
    """Charge la configuration utilisateur.
    Si le fichier n'existe pas, retourne des valeurs par defaut sures.
    """
    if not os.path.exists(path):
        return {
            "capital_monthly": 300,
            "capital_max_available": 600,
            "capital_engaged": 0,
            "max_position_pct": 40,
            "allocation_buy_pct": [15, 40],
            "allocation_progressive_pct": [5, 20],
            "allocation_future_classic_pct": [5, 15],
        }
    with open(path, "r") as f:
        return json.load(f)


def load_portfolio(path="portfolio.json"):
    """Charge les positions reelles de l'utilisateur."""
    if not os.path.exists(path):
        return {"positions": []}
    with open(path, "r") as f:
        return json.load(f)


def compute_capital_available(config):
    """Calcule le capital disponible en soustrayant les engagements."""
    engaged = config.get("capital_engaged", 0)
    max_avail = config.get("capital_max_available", 600)
    monthly = config.get("capital_monthly", 300)
    # Pour l'instant, on suppose que l'enveloppe max est deja atteinte ou non
    # Le calcul precis depend de l'historique des mois, qu'on fera plus tard
    available = min(max_avail, monthly) - engaged
    return max(0, available)


def compute_allocation_frange(config, signal_type):
    """Retourne la fourchette d'investissement en EUR selon le type de signal.
    
    signal_type est l'un de : 'BUY', 'STRONG_BUY', 'PROGRESSIVE', 'FUTURE_CLASSIC'
    """
    available = compute_capital_available(config)

    if signal_type == "BUY":
        pct_lo, pct_hi = config.get("allocation_buy_pct", [15, 40])
    elif signal_type == "PROGRESSIVE":
        pct_lo, pct_hi = config.get("allocation_progressive_pct", [5, 20])
    elif signal_type == "FUTURE_CLASSIC":
        pct_lo, pct_hi = config.get("allocation_future_classic_pct", [5, 15])
    else:
        return (0, 0)

    # Le plafond absolu par position prime sur tout le reste
    max_pos_pct = config.get("max_position_pct", 40)
    pct_hi = min(pct_hi, max_pos_pct)

    lo = round(available * pct_lo / 100)
    hi = round(available * pct_hi / 100)
    return (lo, hi)


def estimate_cycle(median_price, target_buy, n_sales_30d):
    """Estime le stade du cycle (1 a 7) selon des regles simples.

    1 = Invisibilite, 2 = Signal, 3 = Acceleration, 4 = Mainstream,
    5 = FOMO, 6 = Saturation, 7 = Capitulation
    """
    if target_buy is None or median_price is None:
        return (0, "Inconnu")

    ratio = median_price / target_buy  # >1 veut dire que le prix est au-dessus de la cible

    # Heuristique simple : on regarde l'ecart prix/cible + le volume
    if ratio < 0.85:
        # prix bien sous la cible, tres peu de volume
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
    else:
        return (7, "Capitulation")


def decide(item, prix_eur, snap, config):
    """Calcule la decision complete pour un produit.

    Retourne un dictionnaire enrichi avec :
    - decision : le niveau de signal
    - message : le message lisible
    - allocation : la fourchette en EUR
    - cycle : le stade estime
    - categorie : FLIP ou FUTURE_CLASSIC (selon item)
    """
    target = item.get("target_buy")
    strong = item.get("target_strong_buy")
    category = item.get("category", "flip").upper()

    # Determination du niveau
    if strong and prix_eur <= strong:
        niveau = "STRONG_BUY"
        message = f"ACHAT FORT recommande : {prix_eur:.0f} EUR inferieur ou egal a {strong} EUR"
    elif target and prix_eur <= target:
        niveau = "BUY"
        message = f"ACHAT recommande : {prix_eur:.0f} EUR inferieur ou egal a {target} EUR"
    elif target:
        ecart = (prix_eur - target) / target * 100
        niveau = "WAIT"
        message = f"Attendre : {prix_eur:.0f} EUR superieur a {target} EUR (ecart {ecart:+.0f} pourcent)"
    else:
        niveau = "WATCH"
        message = f"Surveiller : {prix_eur:.0f} EUR, pas de cible definie"

    # Allocation recommandee
    if niveau in ("BUY", "STRONG_BUY"):
        alloc = compute_allocation_frange(config, "BUY")
    elif category == "FUTURE_CLASSIC":
        alloc = compute_allocation_frange(config, "FUTURE_CLASSIC")
    else:
        alloc = (0, 0)

    # Stade du cycle
    n_sales = snap.get("sold_count_30d") or snap.get("_n_matched") or 0
    cycle_num, cycle_label = estimate_cycle(
        snap.get("sold_price_median"), target, n_sales
    )

    # Ecart en pourcentage
    ecart_pct = None
    if target:
        ecart_pct = round((prix_eur - target) / target * 100, 1)

    return {
        "decision": niveau,
        "message": message,
        "allocation_eur": alloc,
        "cycle_num": cycle_num,
        "cycle_label": cycle_label,
        "categorie": category,
        "ecart_pct": ecart_pct,
    }