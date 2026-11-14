"""Planification deterministe : question -> corpus -> sous-questions.

Statuts : OK, AMBIGUOUS (marche non identifiable sans hypothese),
NO_DATA (aucun corpus autorise ne couvre la question), INVALID.
Aucune devinette : en cas de doute, on demande une precision.
"""
import re
import unicodedata

MAX_LEN = 500


def norm(text):
    t = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t)


def _hit(q, term):
    return re.search(r"(?<![a-z0-9])" + re.escape(norm(term)) + r"(?![a-z0-9])", q) is not None


def plan_question(question, corpora):
    if not isinstance(question, str) or len(question.strip()) < 5 or len(question) > MAX_LEN:
        return {"status": "INVALID", "reason": f"question vide ou trop longue (5 a {MAX_LEN} caracteres)"}
    q = norm(question)
    named = [c for c in corpora if any(_hit(q, e) for e in c.entities)]
    topical = [c for c in corpora if any(_hit(q, k) for t in c.topics.values() for k in t["keywords"])]
    if len(named) > 1:
        return {"status": "AMBIGUOUS", "reason": "plusieurs marches nommes : preciser lequel analyser",
                "candidates": [c.corpus_id for c in named]}
    if not named:
        if topical:
            return {"status": "AMBIGUOUS", "reason": "aucun marche identifie : preciser le produit ou le marche",
                    "candidates": [c.corpus_id for c in topical]}
        return {"status": "NO_DATA", "reason": "aucun corpus autorise ne couvre cette question"}
    c = named[0]
    topics = [t for t in c.topics.values() if any(_hit(q, k) for k in t["keywords"])] or list(c.topics.values())
    return {"status": "OK", "corpus_id": c.corpus_id,
            "subquestions": [{"subquestion_id": f"sq{i + 1}", "topic_id": t["topic_id"], "question": t["question"]}
                             for i, t in enumerate(topics)]}
