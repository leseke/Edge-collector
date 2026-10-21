"""Verrou de depense a la couche d'execution (R4.2).

Modele : une operation externe = UNE reservation.
  PaidGate.search  -> guard.reserve()      : evenement "reserved"  (debite)
  adaptateur payant -> guard.consume()     : evenement "attempt"   (aucun debit)
  PaidGate         -> guard.record_result(): evenement "result"
  si l'appel externe n'a jamais ete tente -> guard.release() : "released" (re-credite)

- L'adaptateur payant n'appelle JAMAIS reserve() : il exige une reservation
  active, non consommee, pour la meme source et la meme requete. Un appel
  direct (sans PaidGate) est donc refuse, et une reservation ne peut pas
  servir deux fois.
- Le plafond mensuel est verifie et la reservation ecrite sous un VERROU
  INTERPROCESSUS exclusif sur le journal (fcntl sous Linux/macOS, msvcrt
  sous Windows). Si aucun verrou n'est disponible, ou s'il ne peut pas etre
  obtenu dans le delai, la reservation est REFUSEE.
- Un journal prive est obligatoire pour toute depense (tracabilite).
- Une reservation reste debitee si l'appel a ete tente, meme en erreur
  (le fournisseur peut facturer une tentative echouee).
- Le cout est une ESTIMATION ; fixer aussi un plafond cote fournisseur.
"""
import json
import math
import os
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

try:
    import fcntl  # POSIX
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt  # Windows
except ImportError:
    msvcrt = None


class SpendNotAuthorized(RuntimeError):
    pass


def _positive_finite(v, name):
    if isinstance(v, bool) or not isinstance(v, (int, float, str)):
        raise ValueError(f"{name} : nombre attendu")
    try:
        f = float(v)
    except ValueError:
        raise ValueError(f"{name} : nombre attendu") from None
    if not math.isfinite(f) or f <= 0:
        raise ValueError(f"{name} : doit etre fini et strictement positif")
    return f


def parse_policy(raw):
    """Retourne (policy|None, raison_privee). La raison peut contenir des
    montants : elle ne doit jamais etre publiee (voir public_reason)."""
    if not isinstance(raw, dict) or raw.get("authorized") is not True:
        return None, "investigation payante non autorisee (paid_investigation.authorized != true)"
    try:
        max_run = _positive_finite(raw.get("max_usd_per_run"), "max_usd_per_run")
        per_call = _positive_finite(raw.get("est_usd_per_call"), "est_usd_per_call")
        max_month = None
        if raw.get("max_usd_per_month") is not None:
            max_month = _positive_finite(raw["max_usd_per_month"], "max_usd_per_month")
    except ValueError as e:
        return None, f"politique de depense invalide : {e}"
    calls = int(math.floor(max_run / per_call + 1e-9))
    if calls < 1:
        return None, "plafond inferieur au cout d'un appel"
    return {"max_usd_per_run": max_run, "est_usd_per_call": per_call,
            "max_usd_per_month": max_month, "max_calls_per_run": calls}, \
        f"plafond {max_run} USD/run, {per_call} USD/appel estime -> {calls} appel(s) max"


# ------------------------------------------------------------ verrou

LOCK_TIMEOUT_S = 10.0


def lock_supported():
    return fcntl is not None or msvcrt is not None


@contextmanager
def interprocess_lock(path, timeout=LOCK_TIMEOUT_S):
    """Verrou exclusif sur <path>.lock. Leve SpendNotAuthorized si le verrou
    n'est pas disponible sur la plateforme ou pas obtenu dans le delai."""
    if not lock_supported():
        raise SpendNotAuthorized("aucun verrou interprocessus disponible : depense refusee")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd = os.open(path + ".lock", os.O_CREAT | os.O_RDWR, 0o600)
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                if fcntl is not None:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                else:
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise SpendNotAuthorized("verrou du journal de depense indisponible (execution concurrente)")
                time.sleep(0.01)
        yield
    finally:
        try:
            if fcntl is not None:
                fcntl.flock(fd, fcntl.LOCK_UN)
            elif msvcrt is not None:
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        os.close(fd)


# ------------------------------------------------------------ garde

class SpendGuard:
    def __init__(self, policy_raw=None, ledger_path=None, clock=None, lock_timeout=LOCK_TIMEOUT_S):
        self.policy, self.reason = parse_policy(policy_raw)
        self.ledger_path = ledger_path
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.lock_timeout = lock_timeout
        self.allowed = set()
        self._reservations = {}      # id -> dict(state, source, query, est_usd)
        self._active = threading.local()
        self._mutex = threading.Lock()

    @classmethod
    def from_private_file(cls, path="config.private.json", ledger_path=None):
        raw = None
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                raw = json.load(f).get("paid_investigation")
        return cls(raw, ledger_path=ledger_path)

    # -- informations
    @property
    def max_calls(self):
        return self.policy["max_calls_per_run"] if self.policy else 0

    @property
    def public_reason(self):
        """Raison publiable : JAMAIS de montant."""
        if self.policy is None:
            return "investigation payante non autorisee ou politique invalide"
        return "investigation payante autorisee (plafonds prives)"

    @property
    def debited(self):
        return [r for r in self._reservations.values() if r["state"] != "released"]

    @property
    def spent_usd(self):
        return round(sum(r["est_usd"] for r in self.debited), 6)

    def allow(self, queries):
        self.allowed.update(queries)

    # -- journal (appele sous verrou)
    def _append(self, event):
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def _month_debited(self):
        if not os.path.exists(self.ledger_path):
            return 0.0
        month = self.clock().strftime("%Y-%m")
        reserved, released = {}, set()
        with open(self.ledger_path, encoding="utf-8") as f:
            for line in f:
                e = json.loads(line)
                if e.get("event") == "reserved" and str(e.get("at", "")).startswith(month):
                    reserved[e["reservation_id"]] = float(e["est_usd"])
                elif e.get("event") == "released":
                    released.add(e["reservation_id"])
        return sum(v for k, v in reserved.items() if k not in released)

    def _event(self, kind, res_id, **data):
        with interprocess_lock(self.ledger_path, self.lock_timeout):
            self._append({"event": kind, "at": self.clock().isoformat(), "reservation_id": res_id, **data})

    # -- cycle de vie
    def reserve(self, source, query):
        """Reservation atomique (verrou interprocessus). Leve si refusee."""
        if not self.policy:
            raise SpendNotAuthorized(self.reason)
        if not self.ledger_path:
            raise SpendNotAuthorized("journal de depense absent : depense refusee (tracabilite obligatoire)")
        if query not in self.allowed:
            raise SpendNotAuthorized(f"requete non approuvee par l'entonnoir : {query!r}")
        if self.policy["max_usd_per_month"] is not None and os.environ.get("GITHUB_ACTIONS") == "true":
            # Le journal prive ne survit pas a une execution CI : le cumul
            # mensuel ne peut pas y etre garanti.
            raise SpendNotAuthorized("plafond mensuel non garantissable en CI (journal non persistant) : depense refusee")
        cost = self.policy["est_usd_per_call"]
        with self._mutex:
            if len(self.debited) + 1 > self.policy["max_calls_per_run"]:
                raise SpendNotAuthorized("plafond par run atteint")
            with interprocess_lock(self.ledger_path, self.lock_timeout):
                cap_m = self.policy["max_usd_per_month"]
                if cap_m is not None and self._month_debited() + cost > cap_m + 1e-9:
                    raise SpendNotAuthorized("plafond mensuel atteint")
                res_id = uuid.uuid4().hex
                self._append({"event": "reserved", "at": self.clock().isoformat(),
                              "reservation_id": res_id, "source": source, "query": query,
                              "est_usd": cost})
            self._reservations[res_id] = {"state": "reserved", "source": source,
                                          "query": query, "est_usd": cost}
        return res_id

    @contextmanager
    def active(self, res_id):
        self._active.res_id = res_id
        try:
            yield
        finally:
            self._active.res_id = None

    def consume(self, source, query):
        """Appele par l'adaptateur payant juste avant l'appel externe.
        Exige une reservation active, non consommee, pour cette operation.
        Ne debite rien."""
        res_id = getattr(self._active, "res_id", None)
        r = self._reservations.get(res_id) if res_id else None
        if r is None:
            raise SpendNotAuthorized("aucune reservation active : appel payant direct refuse")
        if r["state"] != "reserved":
            raise SpendNotAuthorized("reservation deja utilisee")
        if (r["source"], r["query"]) != (source, query):
            raise SpendNotAuthorized("reservation emise pour une autre operation")
        r["state"] = "attempted"
        self._event("attempt", res_id, source=source, query=query)
        return res_id

    def release(self, res_id, reason):
        r = self._reservations[res_id]
        if r["state"] != "reserved":
            return  # une tentative a eu lieu : la reservation reste debitee
        r["state"] = "released"
        self._event("released", res_id, reason=reason)

    def record_result(self, res_id, outcome, **data):
        self._reservations[res_id]["state"] = "done"
        self._event("result", res_id, outcome=outcome, **data)


class PaidGate:
    """Enveloppe obligatoire d'une source payante : reserve, active la
    reservation pour l'appel, puis enregistre le resultat ou libere."""
    paid = True

    def __init__(self, name, inner, guard):
        if not isinstance(guard, SpendGuard):
            raise TypeError("une source payante exige un SpendGuard")
        self.name = name
        self.inner = inner
        self.guard = guard
        self.cost_per_call = getattr(inner, "cost_per_call", 1)

    def accepts(self, query):
        f = getattr(self.inner, "accepts", None)
        return f(query) if f else True

    def search(self, query, limit=20):
        res_id = self.guard.reserve(self.name, query)  # leve avant tout appel
        attempted = lambda: self.guard._reservations[res_id]["state"] != "reserved"
        try:
            with self.guard.active(res_id):
                out = self.inner.search(query, limit)
        except BaseException as e:
            if attempted():
                self.guard.record_result(res_id, "error", error_type=type(e).__name__)
            else:
                self.guard.release(res_id, f"aucun appel externe tente ({type(e).__name__})")
            raise
        if attempted():
            self.guard.record_result(res_id, "ok", n_results=len(out))
        else:
            # l'enveloppe interne n'a pas atteint la source payante
            self.guard.release(res_id, "aucun appel externe tente")
        return out
