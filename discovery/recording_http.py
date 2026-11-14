"""Transport HTTP qui enregistre chaque reponse brute et met en cache.

- Cache : une meme requete (URL + parametres) n'est pas rejouee avant
  `ttl_hours` (usage raisonnable demande par TCGdex ; Cardmarket est mis a
  jour quotidiennement).
- Enregistrement : chaque reponse est ecrite telle quelle (corps JSON,
  URL, parametres, date, statut) dans un dossier PRIVE. Aucun en-tete
  n'est enregistre (pas de jeton).
- Bilan : self.log contient chaque requete reellement executee ou servie
  par le cache, avec duree et erreur eventuelle.
"""
import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone

from discovery.adapters_official import HttpError
from edge_io import atomic_write_json


class RecordingCachingTransport:
    def __init__(self, inner, directory, ttl_hours=24, clock=None):
        self.inner = inner
        self.dir = directory
        self.ttl = timedelta(hours=ttl_hours)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.log = []
        os.makedirs(directory, exist_ok=True)

    def _key(self, method, url, params):
        raw = json.dumps([method, url, sorted((params or {}).items())], default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:20]

    def get(self, url, params=None, headers=None):
        return self._call("GET", url, params, headers)

    def post(self, url, data=None, headers=None):
        return self._call("POST", url, data, headers)

    def _call(self, method, url, params, headers):
        key = self._key(method, url, params)
        path = os.path.join(self.dir, f"{key}.json")
        now = self.clock()
        entry = {"method": method, "url": url, "params": dict(params or {})}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                rec = json.load(f)
            if now - datetime.fromisoformat(rec["fetched_at"]) < self.ttl and rec.get("status") == 200:
                self.log.append({**entry, "from_cache": True, "status": 200, "duration_s": 0})
                return rec["body"]
        t0 = time.monotonic()
        try:
            body = (self.inner.get(url, params=params, headers=headers) if method == "GET"
                    else self.inner.post(url, data=params, headers=headers))
        except HttpError as e:
            self.log.append({**entry, "from_cache": False, "status": e.status,
                             "duration_s": round(time.monotonic() - t0, 3), "error": str(e)[:200]})
            raise
        except Exception as e:  # DNS, TLS, timeout : erreur explicite
            self.log.append({**entry, "from_cache": False, "status": None,
                             "duration_s": round(time.monotonic() - t0, 3),
                             "error": f"{type(e).__name__}: {str(e)[:160]}"})
            raise
        dur = round(time.monotonic() - t0, 3)
        atomic_write_json(path, {**entry, "fetched_at": now.isoformat(), "status": 200, "body": body})
        self.log.append({**entry, "from_cache": False, "status": 200, "duration_s": dur, "raw_file": path})
        return body

    def summary(self):
        real = [l for l in self.log if not l["from_cache"]]
        return {"http_requests_executed": len(real),
                "served_from_cache": len(self.log) - len(real),
                "errors": [l for l in real if l.get("error")],
                "requests": self.log}
