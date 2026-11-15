"""Registre deterministe de l'equipe multi-agents EDGE (sans appels IA).

Ce module ne contacte aucun fournisseur et n'engage aucune depense.
Il transforme un sujet TCG et ses sous-questions en plan de delegation
explicite. L'execution des agents sera branchee dans une etape ulterieure,
derriere les contrats, preuves et SpendGuard deja existants.
"""
from dataclasses import dataclass
import re
import unicodedata

TEAM_CONTRACT = "edge.agent_team.v1"

TCG_CATEGORIES = {
    "tcg", "trading_card_game", "tcg_related", "tcg_accessory",
    "tcg_collectible",
}


@dataclass(frozen=True)
class AgentRole:
    agent_id: str
    purpose: str
    keywords: tuple


# Les roles sont des competences, pas des instances de modeles.
# Plusieurs roles peuvent etre confies au meme fournisseur selon la tache.
AGENT_ROLES = (
    AgentRole("market_intelligence", "Prix, ventes conclues, volumes, liquidite et dynamique de marche.",
              ("prix", "price", "vente", "sold", "volume", "liquidite", "liquidity", "spread", "marche", "market")),
    AgentRole("supply_distribution", "Offre, distribution, stocks, reimpressions, sorties et retraits.",
              ("offre", "supply", "stock", "disponibilite", "availability", "distribution", "reprint",
               "reimpression", "retire", "retirement", "rupture", "precommande", "preorder", "launch", "sortie")),
    AgentRole("actor_community", "Acteurs, plateformes, boutiques, influenceurs et communautes.",
              ("acteur", "actor", "vendeur", "seller", "boutique", "platform", "plateforme", "influenceur",
               "community", "communaute", "collectionneur", "collector")),
    AgentRole("hype_intelligence", "Attention, propagation de hype, FOMO, saturation et retournement.",
              ("hype", "fomo", "attention", "tendance", "trend", "buzz", "saturation", "viral", "social")),
    AgentRole("grading_intelligence", "Organismes de grading, populations, tarifs, delais et capacite.",
              ("grading", "psa", "cgc", "bgs", "population", "pop report", "delai", "turnaround",
               "soumission", "submission", "slab")),
    AgentRole("grading_arbitrage", "Arbitrage brut/grade, probabilites de notes et rentabilite nette.",
              ("arbitrage", "grade", "raw", "brut", "psa 10", "cout total", "roi", "rentabilite")),
    AgentRole("restoration_preservation", "Conservation, restauration, nettoyage et integrite des cartes.",
              ("restauration", "restoration", "conservation", "preservation", "nettoyage", "cleaning",
               "retouche", "alteration", "condition")),
    AgentRole("error_card_intelligence", "Erreurs d'impression, variantes et demande specifique.",
              ("erreur", "error", "misprint", "miscut", "crimp", "off-center", "defaut impression")),
    AgentRole("private_demand", "Bounties, recherches privees et demandes verifiables.",
              ("bounty", "bounties", "wanted", "recherche privee", "private demand", "demande privee")),
)


class TCGScopeError(ValueError):
    """Le sujet n'est pas explicitement rattache a l'ecosysteme TCG."""


def _norm(value):
    value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def is_tcg_subject(subject):
    """Accepte uniquement une categorie TCG explicite ou un lien TCG explicite."""
    if not isinstance(subject, dict):
        return False
    category = _norm(subject.get("category")).replace(" ", "_")
    if category in TCG_CATEGORIES:
        return True
    if subject.get("tcg_link") is True:
        return True
    linked_game = subject.get("related_tcg")
    return isinstance(linked_game, str) and bool(linked_game.strip())


def require_tcg_scope(subject):
    if not is_tcg_subject(subject):
        raise TCGScopeError("sujet hors perimetre : un lien direct et identifiable avec un TCG est requis")


def route_topics(subject, topics, include_synthesis=True):
    """Retourne les roles a activer, sans les executer ni appeler de modele.

    topics accepte des dictionnaires (topic_id/question) ou des chaines.
    Le coordinateur est toujours present; les specialistes ne sont ajoutes
    que si leurs mots-cles correspondent au sujet ou aux sous-questions.
    """
    require_tcg_scope(subject)
    chunks = [subject.get("title", ""), subject.get("market", "")]
    chunks.extend(subject.get("tags", []) if isinstance(subject.get("tags"), list) else [])
    for topic in topics or []:
        if isinstance(topic, dict):
            chunks.extend((topic.get("topic_id", ""), topic.get("question", "")))
        else:
            chunks.append(topic)
    haystack = f" {_norm(' '.join(str(x) for x in chunks))} "
    selected = ["coordinator"]
    for role in AGENT_ROLES:
        if any(re.search(r"(?<![a-z0-9])" + re.escape(_norm(k)) + r"(?![a-z0-9])", haystack)
               for k in role.keywords):
            selected.append(role.agent_id)
    if include_synthesis:
        selected.append("opportunity_detection")
    return {
        "contract": TEAM_CONTRACT,
        "scope": "tcg",
        "agent_ids": selected,
        "execution": "not_started",
        "paid_calls": 0,
    }


def build_team_plan(subject, subquestions):
    """Construit un plan de delegation par sous-question, sans executer d'agent."""
    require_tcg_scope(subject)
    tasks = []
    all_roles = []
    for sq in subquestions or []:
        routed = route_topics(subject, [sq], include_synthesis=False)
        specialists = [agent_id for agent_id in routed["agent_ids"] if agent_id != "coordinator"]
        for agent_id in specialists:
            if agent_id not in all_roles:
                all_roles.append(agent_id)
        tasks.append({
            "subquestion_id": sq.get("subquestion_id"),
            "topic_id": sq.get("topic_id"),
            "assigned_roles": specialists,
            "status": "planned",
        })
    return {
        "contract": TEAM_CONTRACT,
        "scope": "tcg",
        "coordinator": "coordinator",
        "specialist_roles": all_roles,
        "synthesis_role": "opportunity_detection",
        "tasks": tasks,
        "execution": "planned_only",
        "paid_calls": 0,
    }
