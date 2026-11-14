"""Traduit une recherche libre en campagne Discovery. Deterministe :
pas de modele de langage, donc pas de requete inventee hors regles."""
import hashlib
import re

from discovery.campaigns import validate_campaign
from discovery.identity import fold, slug

ENTITIES = {
    "lego": "LEGO", "pokemon": "Pokemon", "one piece": "One Piece",
    "lorcana": "Lorcana", "riftbound": "Riftbound", "magic": "Magic The Gathering",
    "console": "console retro", "consoles": "console retro", "nintendo": "Nintendo",
    "playstation": "PlayStation", "game boy": "Game Boy", "star wars": "Star Wars",
    "harry potter": "Harry Potter", "zelda": "Zelda", "mario": "Mario",
}
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


def detect(text):
    t = fold(text)
    ents = []
    for k, v in ENTITIES.items():
        if re.search(r"\b" + re.escape(k) + r"\b", t) and v not in ents:
            ents.append(v)
    intents = [fam for fam, toks in INTENTS if any(tok in t for tok in toks)]
    # "30 ans de Pokemon" = anniversaire ; "sur cinq ans" = horizon
    if re.search(r"\b\d{1,3} ans (de|d')", t) and "catalyst" not in intents:
        intents.insert(0, "catalyst")
    sets = re.findall(r"(?<!\d)(\d{4,6})(?!\d)", t)
    sets = [s for s in sets if not 1950 <= int(s) <= 2040]
    horizon = "FUTURE_CLASSIC" if re.search(r"(cinq|5|dix|10|plusieurs)\s*ans|long terme", t) else "FLIP"
    return ents, intents or ["price_anomaly", "rarity"], sets, horizon


# Univers par defaut quand la recherche ne nomme aucune licence/marque :
# les categories cibles de l'activite (modifiable).
DEFAULT_UNIVERSE = ["LEGO", "Pokemon", "One Piece"]


def plan(text, mode="discovery", horizon=None, max_queries=6, universe=None):
    if not isinstance(text, str) or not text.strip() or len(text) > 200:
        raise ValueError("recherche vide ou trop longue")
    ents, intents, sets, auto_h = detect(text)
    strategy = horizon or auto_h
    # Une phrase libre n'est envoyee telle quelle que si elle nomme
    # une licence ou une reference : sinon elle est inexploitable en recherche.
    queries = [text.strip()] if (ents or sets) else []
    for s in sets:
        queries.append(f"LEGO {s}" if "LEGO" in ents or not ents else s)
    bases = [" ".join(ents)] if ents else list(universe or DEFAULT_UNIVERSE)
    for fam in intents:
        for suf in SUFFIXES[fam]:
            for base in bases:
                queries.append(f"{base} {suf}")
    seen, uniq = set(), []
    for q in queries:
        k = fold(q)
        if k not in seen:
            seen.add(k)
            uniq.append(q)
    uniq = uniq[:max_queries]
    family = "price_anomaly" if mode == "investigation" else intents[0]
    sources = ["scavio_retail_fr", "ebay_sold"] if (mode == "investigation" or sets) else ["scavio_retail_fr"]
    cid = "lab-" + (slug(text, 4) or "q")[:40] + "-" + hashlib.sha256(f"{text}|{mode}|{strategy}".encode()).hexdigest()[:6]
    campaign = {
        "id": cid, "family": family, "queries": uniq, "sources": sources,
        "expansion_sources": ["ebay_sold"], "max_calls": max(len(uniq) * len(sources), 4) + 4,
        "max_expansions": 0 if mode == "investigation" else 4, "limit_per_query": 20,
        "origin": "searchlab", "user_query": text.strip(), "mode": mode, "strategy": strategy,
        "detected": {"entities": ents, "intents": intents, "set_numbers": sets,
                     "universe": None if ents else bases},
    }
    errs = validate_campaign(campaign)
    if errs:
        raise ValueError(f"campagne invalide : {errs}")
    return campaign
