"""Registre d'acces aux sources : une source n'est interrogee que si ses
conditions ont ete verifiees par l'utilisateur ET si ses identifiants sont
presents. Sinon l'indisponibilite est explicite (jamais silencieuse)."""
import json
import os

from discovery.adapters import SourceUnavailable

DEFAULT_REGISTRY = os.path.join(os.path.dirname(__file__), "sources_access.json")


def load_registry(path=DEFAULT_REGISTRY):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["sources"]


def access_status(name, registry, environ=None):
    env = os.environ if environ is None else environ
    s = registry.get(name)
    if s is None:
        return {"source": name, "usable": False, "reason": "source inconnue du registre"}
    missing = [v for v in s.get("env", []) if not env.get(v)]
    reasons = []
    if s.get("status") != "VERIFIED":
        reasons.append("conditions/licence/quotas non verifies (status != VERIFIED)")
    if missing:
        reasons.append("identifiants absents : " + ", ".join(missing))
    return {"source": name, "usable": not reasons, "reason": "; ".join(reasons) or "ok",
            "paid": s.get("paid", False), "quota_per_run": s.get("quota_per_run"),
            "documented_quota_per_day": s.get("documented_quota_per_day")}


class GatedAdapter:
    """Enveloppe : applique le registre et le quota par run avant tout appel."""

    def __init__(self, name, inner, registry, environ=None):
        self.name = name
        self.inner = inner
        self.registry = registry
        self.environ = environ
        self.calls = 0
        self.cost_per_call = getattr(inner, "cost_per_call", 1)
        self.paid = registry.get(name, {}).get("paid", False)

    def accepts(self, query):
        f = getattr(self.inner, "accepts", None)
        return f(query) if f else True

    def search(self, query, limit=20):
        st = access_status(self.name, self.registry, self.environ)
        if not st["usable"]:
            raise SourceUnavailable(f"{self.name} : {st['reason']}")
        q = st.get("quota_per_run")
        if q is not None and self.calls >= q:
            raise SourceUnavailable(f"{self.name} : quota par run atteint ({q})")
        self.calls += 1
        return self.inner.search(query, limit)
