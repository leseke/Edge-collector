"""Raisonnement par catalyseurs.

Chaine : Evenement -> Changement comportemental -> Demande potentielle
-> Produits concernes -> Offre disponible -> Ecart de valorisation.

Chaque maillon est soit etaye par une donnee observee, soit marque
HYPOTHESE. Le module cherche aussi ce qui invaliderait la these.
"""
import json
import os
from datetime import date

from discovery.identity import fold
from discovery.signals import quantile

_DEFAULT = os.path.join(os.path.dirname(__file__), "catalysts.json")

BEHAVIOR = {
    "anniversary": "regain d'attention nostalgique et editions commemoratives",
    "media_release": "afflux de nouveaux fans et retour des anciens autour de la licence",
    "game_announcement": "hausse d'interet de la communaute de joueurs",
    "retirement": "offre neuve qui se tarit apres l'arret de production",
    "license_extension": "nouveaux produits attirant un public elargi",
    "trend_revival": "retour d'une esthetique ou d'une mode",
}
COMPETING = {
    "anniversary": ["les editions commemoratives peuvent capter la demande au detriment des anciens produits",
                    "l'effet peut etre deja integre aux prix (evenement connu de longue date)"],
    "media_release": ["l'oeuvre peut decevoir", "des reeditions peuvent accompagner la sortie"],
    "retirement": ["stocks importants chez les revendeurs", "reedition ou produit de remplacement"],
}
DEFAULT_COMPETING = ["correlation sans causalite", "evenement deja connu et anticipe par le marche"]


def load_catalysts(path=_DEFAULT):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["catalysts"]


def match(name, catalysts):
    t = fold(name)
    return [c for c in catalysts if any(fold(k) in t for k in c.get("keywords", []))]


def _momentum(sold_obs, as_of):
    """Mediane 30 derniers jours vs 31-120 jours. None si donnees insuffisantes."""
    recent, prior = [], []
    for o in sold_obs:
        d = (as_of - date.fromisoformat(o["observed_at"][:10])).days
        if 0 <= d <= 30:
            recent.append(o["price_eur"])
        elif 30 < d <= 120:
            prior.append(o["price_eur"])
    if len(recent) < 3 or len(prior) < 3:
        return None
    return quantile(recent, 0.5) / quantile(prior, 0.5) - 1


def evaluate_chain(catalyst, product_name, observations, as_of):
    sold = [o for o in observations if o["evidence_type"] == "SOLD"]
    buyable = [o for o in observations if o["evidence_type"] in ("ASKING_PRICE", "RETAIL_OFFER")]
    ev_date = date.fromisoformat(catalyst["date"])
    days_to = (ev_date - as_of).days
    mom = _momentum(sold, as_of)
    links = [
        {"step": "Evenement", "content": catalyst["title"],
         "status": "VERIFIE" if catalyst.get("verified") and catalyst.get("source_url") else "NON_VERIFIE",
         "source_url": catalyst.get("source_url")},
        {"step": "Changement comportemental", "content": BEHAVIOR.get(catalyst["type"], "non modelise"),
         "status": "HYPOTHESE"},
        {"step": "Demande potentielle", "content": "hausse de demande pour les produits lies",
         "status": "HYPOTHESE"},
        {"step": "Produit concerne", "content": product_name, "status": "CORRESPONDANCE_MOT_CLE"},
        {"step": "Offre disponible", "content": f"{len(buyable)} offre(s) observee(s)",
         "status": "OBSERVE" if buyable else "INCONNU"},
        {"step": "Ecart de valorisation",
         "content": ("dynamique des ventes conclues : " + (f"{mom:+.0%} (30j vs 31-120j)" if mom is not None else "non mesurable")),
         "status": "OBSERVE" if mom is not None else "INCONNU"},
    ]
    already_priced = mom is not None and mom > 0.2
    competing = COMPETING.get(catalyst["type"], []) + DEFAULT_COMPETING
    if already_priced:
        competing = ["hausse recente deja visible : l'evenement semble en partie integre"] + competing
    if days_to < 0:
        competing = [f"evenement passe depuis {-days_to} jours : effet d'anticipation potentiellement epuise"] + competing
    return {
        "catalyst_id": catalyst["id"], "event_date": catalyst["date"], "days_to_event": days_to,
        "chain": links,
        "momentum_30d_vs_prior": round(mom, 3) if mom is not None else None,
        "competing_explanations": competing,
        "invalidation_tests": [
            "annonce de reedition ou reapprovisionnement massif",
            "ventes conclues stables ou en baisse a l'approche de l'evenement",
            "hausse des offres disponibles (vendeurs qui anticipent aussi)",
        ],
        "supports_thesis": bool(buyable) and catalyst.get("verified", False) and not already_priced and days_to > 0,
        "disclaimer": "Un evenement annonce n'est pas une preuve de hausse future.",
    }
