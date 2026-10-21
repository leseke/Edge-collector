"""Transport HTTP rejoue depuis des fixtures (pilote hors reseau).

Les reponses imitent les formats documentes des API ; leurs valeurs sont
FICTIVES. Toute observation produite est marquee simulated=True.
"""
import json

from discovery.adapters_official import HttpError


class FixtureTransport:
    def __init__(self, path):
        with open(path, encoding="utf-8") as f:
            self.routes = json.load(f)["routes"]
        self.log = []

    def _find(self, method, url, params):
        for r in self.routes:
            if r["method"] == method and r["url"] == url and all(
                    str((params or {}).get(k)) == str(v) for k, v in r.get("match", {}).items()):
                return r
        return None

    def get(self, url, params=None, headers=None):
        return self._resp("GET", url, params)

    def post(self, url, data=None, headers=None):
        return self._resp("POST", url, data)

    def _resp(self, method, url, params):
        self.log.append((method, url, dict(params or {})))
        r = self._find(method, url, params)
        if r is None:
            raise HttpError(404, f"fixture absente {method} {url}")
        if r.get("status", 200) != 200:
            raise HttpError(r["status"])
        return r["response"]


class SimulatedMarker:
    """Marque chaque observation comme simulee (jamais confondue avec du reel)."""

    def __init__(self, inner):
        self.inner = inner
        self.name = inner.name
        self.cost_per_call = getattr(inner, "cost_per_call", 0)
        self.paid = getattr(inner, "paid", False)

    def accepts(self, query):
        f = getattr(self.inner, "accepts", None)
        return f(query) if f else True

    def search(self, query, limit=20):
        return [dict(o, simulated=True) for o in self.inner.search(query, limit)]
