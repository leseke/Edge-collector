"""Conformite d'une sortie d'agent AVANT ingestion (complete AI-001.1).

Bloque ce que l'ingestion AI-001.1 laissait passer (diagnostic AI-002A) :
chiffres inventes dans le texte, citations incoherentes ou alterees,
instructions recopiees depuis des sources tierces, graphiques sans donnees.
Toute violation = sortie rejetee en bloc, rien n'est stocke.
"""
import re

ALLOWED_KEYS = {"claims", "agent_opinion", "chart_requests", "notes"}
INJECTION_RE = re.compile(
    r"(ignore|oublie|disregard|override|neglige)\w*\W+(?:\w+\W+){0,6}?(instruction|consigne|regle|prompt)"
    r"|edge_decision|strong_buy|(?<![a-z])buy(?![a-z])|\balloue|allocation|system\s*prompt|<\s*script"
    r"|achetez|acheter maintenant|passe(?:z)? la decision", re.I)
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


TAGGED_RE = re.compile(r"(\d+(?:[.,]\d+)?)(\s*(?:%|pour\s*cent|points?\s+de\s+pourcentage))?", re.I)


def tagged_numbers(text):
    """Nombres etiquetes : '29.8%' pour un pourcentage, '545' sinon. Un nombre
    brut ne peut pas justifier un pourcentage (et inversement)."""
    out = set()
    for num, pct in TAGGED_RE.findall(str(text)):
        n = num.replace(",", ".")
        out.add(n + "%" if pct else n)
    return out


def suspicious(text):
    return bool(INJECTION_RE.search(str(text)))


def numbers(text):
    return {n.replace(",", ".") for n in NUMBER_RE.findall(str(text))}


def check_agent_output(output, inventory, allowed_numbers=None):
    """inventory : {"sources": {id: src}, "extracts": {id: extrait autorise},
    "datasets": {id: dataset}}. Retourne la liste des violations."""
    V = []
    if not isinstance(output, dict):
        return ["sortie non structuree"]
    extra = set(output) - ALLOWED_KEYS
    if extra:
        V.append(f"champ interdit pour un agent : {sorted(extra)}")
    by_source = {}
    for e in inventory["extracts"].values():
        by_source.setdefault(e["source_id"], []).append(e)
    for c in output.get("claims", []) or []:
        cid = c.get("claim_id")
        st = str(c.get("statement", ""))
        cited = list(c.get("source_ids", []) or [])
        for sid in cited + list(c.get("contradicting_source_ids", []) or []):
            if sid not in inventory["sources"]:
                V.append(f"{cid} : source inconnue ou non autorisee {sid!r}")
        if suspicious(st):
            V.append(f"{cid} : instruction suspecte recopiee (contenu tiers)")
        cited_ext = [e for s in cited for e in by_source.get(s, [])]
        if c.get("kind") == "fact":
            if not any(e["statement"] == st for e in cited_ext):
                V.append(f"{cid} : citation incoherente (enonce absent des extraits des sources citees)")
        else:
            allowed = set().union(*(tagged_numbers(e["statement"]) for e in cited_ext)) if cited_ext else set()
            # (AI-002B) nombres issus de calculs EDGE references par une interpretation
            allowed |= (allowed_numbers or {}).get(cid, set())
            extra_n = tagged_numbers(st) - allowed
            if extra_n:
                V.append(f"{cid} : chiffre non justifie par une source citee {sorted(extra_n)}")
    op = output.get("agent_opinion")
    if op is not None:
        if suspicious(op.get("rationale", "")) or suspicious(op.get("stance", "")):
            V.append("avis de l'agent : instruction ou decision suspecte")
        if numbers(op.get("rationale", "")):
            V.append("avis de l'agent : chiffre non justifie")
    for i, ch in enumerate(output.get("chart_requests", []) or []):
        ds = []
        for did in ch.get("dataset_ids", []) or []:
            d = inventory["datasets"].get(did)
            if d is None:
                V.append(f"graphique {i + 1} : dataset inconnu ou non autorise {did!r}")
            elif not any(p["value"] is not None for p in d["points"]):
                V.append(f"graphique {i + 1} : dataset {did} sans aucune donnee")
            else:
                ds.append(d)
        if len({(d["unit"], d["currency"]) for d in ds}) > 1:
            V.append(f"graphique {i + 1} : unites ou devises differentes")
        if suspicious(ch.get("title", "")):
            V.append(f"graphique {i + 1} : titre suspect")
    if suspicious(output.get("notes", "")):
        V.append("notes : instruction suspecte")
    return V
