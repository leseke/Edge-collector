"""Entonnoir : investigation payante reservee aux candidats ayant franchi
un premier filtrage economique avec des preuves gratuites.

Aucune depense sans autorisation explicite ET plafond chiffre :
config.private.json -> "paid_investigation": {
    "authorized": true, "max_usd_per_run": 1.0, "est_usd_per_call": 0.125 }
Si le cout par appel est inconnu, aucun appel n'est autorise (on ne peut
pas borner une depense inconnue).
"""

ELIGIBLE_DECISIONS = ("WATCH", "BUY")


def eligible(investigations):
    """Candidats dont l'indice gratuit justifie une confirmation : decision
    WATCH/BUY, offre achetable, et valorisation qui ne repose PAS deja sur
    des ventes individuelles (la confirmation n'apporterait rien)."""
    out = []
    for inv in investigations:
        if inv["decision"] not in ELIGIBLE_DECISIONS or not inv.get("best_offer"):
            continue
        if inv.get("valuation_basis") == "INDIVIDUAL_SALES":
            continue
        if not inv["product_key"].startswith("lego:") and not inv.get("reasons"):
            continue
        out.append(inv["product_key"])
    return out


def paid_budget(config):
    """Retourne (max_calls, raison). 0 si non autorise ou invalide
    (NaN, infini, booleen, negatif, nul, texte : tous refuses)."""
    from investigation.spend import parse_policy
    pol, why = parse_policy((config or {}).get("paid_investigation"))
    return (pol["max_calls_per_run"] if pol else 0), why


def query_for(product_key):
    if product_key.startswith("lego:") and "+" not in product_key:
        return "LEGO " + product_key.split(":", 1)[1]
    return None
