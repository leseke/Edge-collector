"""Traduit une recherche libre en campagne Discovery TCG.
Deterministe : aucun modele de langage et aucune requete inventee hors regles.
"""
import hashlib
import re

from discovery.campaigns import validate_campaign
from discovery.identity import fold, slug

ENTITIES = {
    "pokemon": "Pokemon",
    "one piece": "One Piece",
    "lorcana": "Lorcana",
    "riftbound": "Riftbound",
    "magic": "Magic The Gathering",
    "yu gi oh": "Yu-Gi-Oh!",
    "yugioh": "Yu-Gi-Oh!",
    "digimon": "Digimon Card Game",
    "flesh and blood": "Flesh and Blood",
    "weiss schwarz": "Weiss Schwarz",
    "union arena": "Union Arena",
    "dragon ball": "Dragon Ball Super Card Game",
    "star wars unlimited": "Star Wars Unlimited",
    "tcg": "TCG multi-jeux",
}
OUT_OF_SCOPE = (
    "lego", "funko", "console", "consoles", "nintendo",
    "playstation", "game boy",
)
INTENTS = [
    ("end_of_life", ("fin de", "arret", "s'arrete", "retir", "rupture", "fin de serie", "discontinu")),
    ("catalyst", ("anniversaire", "film", "jeu video", "annonce", "sortie")),
    ("price_anomaly", ("sous-evalu", "sous evalu", "erreur de prix", "promo", "bon plan", "liquidation", "destockage")),
    ("rarity", ("collection", "rare", "prometteur", "limite", "collector")),
    ("emerging", ("emergent", "nouveau", "tendance", "nouveaute")),
]
SUFFIXES = {
    "end_of_life": ["fin de serie", "bientot retire"],
    "catalyst": ["anniversaire", "collector"],
    "price_anomaly": ["promo", "destockage"],
    "rarity": ["edition limitee"],
    "emerging": ["nouveaute"],
}
DEFAULT_UNIVERSE = [
    "Pokemon", "One Piece", "Magic The Gathering", "Yu-Gi-Oh!",
    "Disney Lorcana", "Digimon Card Game", "Riftbound",
    "Flesh and Blood", "Weiss Schwarz", "Union Arena",
    "Dragon Ball Super Card Game", "Star Wars Unlimited",
]


def detect(text):
    t = fold(text)
    ents = []
    for key, value in ENTITIES.items():
        if re.search(r"\b" + re.escape(key) + r"\b", t) and value not in ents:
            ents.append(value)
    intents = [family for family, tokens in INTENTS if any(token in t for token in tokens)]
    # "30 ans de Pokemon" = anniversaire ; "sur cinq ans" = horizon.
    if re.search(r"\b\d{1,3} ans (de|d')", t) and "catalyst" not in intents:
        intents.insert(0, "catalyst")
    sets = re.findall(r"(?<!\d)(\d{3,6})(?!\d)", t)
    sets = [number for number in sets if not 1950 <= int(number) <= 2040]
    horizon = "FUTURE_CLASSIC" if re.search(r"(cinq|5|dix|10|plusieurs)\s*ans|long terme", t) else "FLIP"
    return ents, intents or ["price_anomaly", "rarity"], sets, horizon


def _contains_out_of_scope(text):
    normalized = fold(text)
    return [term for term in OUT_OF_SCOPE if re.search(r"\b" + re.escape(term) + r"\b", normalized)]


def plan(text, mode="discovery", horizon=None, max_queries=6, universe=None):
    if not isinstance(text, str) or not text.strip() or len(text) > 200:
        raise ValueError("recherche vide ou trop longue")
    outside = _contains_out_of_scope(text)
    if outside:
        raise ValueError("hors perimetre EDGE TCG : " + ", ".join(outside))
    ents, intents, sets, auto_horizon = detect(text)
    strategy = horizon or auto_horizon
    selected_universe = list(DEFAULT_UNIVERSE if universe is None else universe)
    allowed = {fold(name) for name in DEFAULT_UNIVERSE}
    if any(not isinstance(name, str) or fold(name) not in allowed for name in selected_universe):
        raise ValueError("l'univers de recherche doit rester limite aux jeux TCG EDGE")
    if not selected_universe:
        raise ValueError("univers TCG vide")
    queries = [text.strip()] if (ents or sets) else []
    for number in sets:
        base = " ".join(ents) if ents else selected_universe[0]
        queries.append(f"{base} {number}")
    bases = [" ".join(ents)] if ents else selected_universe
    for family in intents:
        for suffix in SUFFIXES[family]:
            for base in bases:
                queries.append(f"{base} {suffix}")
    seen, unique = set(), []
    for query in queries:
        key = fold(query)
        if key not in seen:
            seen.add(key)
            unique.append(query)
    unique = unique[:max_queries]
    family = "price_anomaly" if mode == "investigation" else intents[0]
    sources = ["scavio_retail_fr", "ebay_sold"] if (mode == "investigation" or sets) else ["scavio_retail_fr"]
    campaign_id = "lab-" + (slug(text, 4) or "q")[:40] + "-" + hashlib.sha256(
        f"{text}|{mode}|{strategy}".encode()
    ).hexdigest()[:6]
    campaign = {
        "id": campaign_id, "family": family, "queries": unique, "sources": sources,
        "expansion_sources": ["ebay_sold"], "max_calls": max(len(unique) * len(sources), 4) + 4,
        "max_expansions": 0 if mode == "investigation" else 4, "limit_per_query": 20,
        "origin": "searchlab", "user_query": text.strip(), "mode": mode, "strategy": strategy,
        "detected": {
            "entities": ents, "intents": intents, "set_numbers": sets,
            "universe": None if ents else bases,
        },
    }
    errors = validate_campaign(campaign)
    if errors:
        raise ValueError(f"campagne invalide : {errors}")
    return campaign
