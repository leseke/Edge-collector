"""Stockage public des rapports : historique IMMUABLE, corrections versionnees.

data/intelligence/
  index.json                            liste des versions (empreintes SHA-256)
  reports/<report_id>/v0001.json        une version = un fichier, jamais reecrit

- Publication refusee si : rapport invalide, donnee privee detectee, version
  deja existante, version precedente absente, empreinte de la version
  remplacee differente de celle stockee.
- Ecriture exclusive (O_EXCL) : aucun ecrasement possible, meme en concurrence.
- verify() recalcule chaque empreinte et detecte toute alteration.
"""
import hashlib
import json
import os

from edge_engine import assert_no_private_leak
from edge_io import atomic_write_json
from intelligence.validator import DEFAULT_MAX_DATA_AGE_DAYS, assess, canonical_json, content_sha256
from investigation.spend import interprocess_lock


class PublishRefused(RuntimeError):
    pass


def _write_exclusive(path, data):
    """Creation exclusive (jamais d'ecrasement) + fsync du fichier."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def _fsync_dir(path):
    """Durabilite des creations/renommages (POSIX). Sans effet sous Windows."""
    if os.name != "posix":
        return
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


INQUIRY_PREFIX = "eir_q-"


def _is_inquiry(report):
    """Espace d'identifiants reserve aux enquetes d'agent (AI-002A/B) : un tel
    rapport n'est jamais publie sans son dossier. Les rapports anterieurs ou
    rediges a la main (autres identifiants) restent publiables seuls."""
    return str(report.get("report_id", "")).startswith(INQUIRY_PREFIX)


class ReportStore:
    def __init__(self, root=os.path.join("data", "intelligence")):
        self.root = root
        self.index_path = os.path.join(root, "index.json")

    def _version_path(self, report_id, version):
        return os.path.join(self.root, "reports", report_id, f"v{version:04d}.json")

    def load_index(self):
        if not os.path.exists(self.index_path):
            return {"schema_version": 1, "reports": []}
        with open(self.index_path, encoding="utf-8") as f:
            return json.load(f)

    def read(self, report_id, version=None):
        idx = [e for e in self.load_index()["reports"] if e["report_id"] == report_id]
        if not idx:
            raise KeyError(report_id)
        e = max(idx, key=lambda x: x["report_version"]) if version is None else \
            next(x for x in idx if x["report_version"] == version)
        with open(os.path.join(self.root, e["path"]), encoding="utf-8") as f:
            return json.load(f)

    def publish(self, report, dossier=None):
        """Publication en deux phases (AI-002B).
        1. validations (rapport, dossier, coherence, donnees privees) ;
        2. ecriture exclusive du rapport puis du dossier (fsync) ;
        3. POINT DE VALIDATION : remplacement atomique de l'index.
        Toute erreur avant 3 supprime les fichiers crees : rien n'est publie.
        Une interruption brutale avant 3 laisse des fichiers NON REFERENCES :
        verify() les signale, recover() les met en quarantaine.
        Un rapport contenant des affirmations d'agent exige son dossier."""
        a = assess(report)
        if not a["valid"]:
            raise PublishRefused("rapport invalide : " + "; ".join(a["errors"][:5]))
        try:
            assert_no_private_leak(report)
        except ValueError as e:
            raise PublishRefused(f"donnee privee : {e}") from None
        rid, ver = report["report_id"], report["report_version"]
        sha = content_sha256(report)
        dossier_bytes = None
        if dossier is None and _is_inquiry(report):
            raise PublishRefused("rapport d'enquete d'agent (eir_q-*) sans dossier : publication refusee")
        if dossier is not None:
            if (dossier.get("report_id"), dossier.get("report_version")) != (rid, ver):
                raise PublishRefused("dossier d'un autre rapport ou d'une autre version")
            if dossier.get("report_sha256") != sha:
                raise PublishRefused("dossier ne correspondant pas au contenu du rapport")
            try:
                from intelligence.dossier import check_dossier_public
                check_dossier_public(dossier)
            except ValueError as e:
                raise PublishRefused(f"dossier non publiable : {e}") from None
            dossier_bytes = canonical_json(dossier).encode("utf-8")
        path = self._version_path(rid, ver)
        dpath = os.path.join(self.root, "dossiers", rid, f"v{ver:04d}.json")
        with interprocess_lock(self.index_path):
            idx = self.load_index()
            mine = {e["report_version"]: e for e in idx["reports"] if e["report_id"] == rid}
            if ver in mine or os.path.exists(path):
                raise PublishRefused(f"{rid} v{ver} existe deja : l'historique publie est immuable")
            if dossier_bytes is not None and os.path.exists(dpath):
                raise PublishRefused(f"dossier {rid} v{ver} deja present (publication interrompue ? lancer recover())")
            if ver > 1:
                prev = mine.get(ver - 1)
                if prev is None:
                    raise PublishRefused(f"{rid} v{ver - 1} absente : publier les versions dans l'ordre")
                if report["supersedes"]["content_sha256"] != prev["content_sha256"]:
                    raise PublishRefused("empreinte de la version remplacee differente de la version publiee")
            elif any(e["report_id"] == rid for e in idx["reports"]):
                raise PublishRefused(f"{rid} existe deja")
            created = []
            try:
                _write_exclusive(path, canonical_json(report).encode("utf-8"))
                created.append(path)
                if dossier_bytes is not None:
                    _write_exclusive(dpath, dossier_bytes)
                    created.append(dpath)
                entry = {"report_id": rid, "report_version": ver, "content_sha256": sha,
                         "path": os.path.relpath(path, self.root).replace(os.sep, "/"),
                         "title": report["subject"]["title"], "market": report["subject"]["market"],
                         "region": report["subject"]["region"], "created_at": report["created_at"],
                         "production_status": report["production_status"], "simulated": report["simulated"],
                         "verification_level": a["verification_level"], "label": a["label"],
                         "edge_decision": report["decisions"]["edge_decision"]["decision"],
                         "data_as_of": report["data_as_of"],
                         "max_data_age_days": a["timeliness"]["max_age_days"],
                         "freshness_policy": a["timeliness"]["policy"]}
                if dossier_bytes is not None:
                    import hashlib
                    entry["dossier_path"] = os.path.relpath(dpath, self.root).replace(os.sep, "/")
                    entry["dossier_sha256"] = hashlib.sha256(dossier_bytes).hexdigest()
                idx["reports"].append(entry)
                assert_no_private_leak(idx)
                atomic_write_json(self.index_path, idx)  # point de validation
                _fsync_dir(self.root)
            except BaseException:
                for p in reversed(created):  # non references par l'index : suppression sure
                    try:
                        os.remove(p)
                    except OSError:
                        pass
                raise
        return entry

    def recover(self):
        """Met en quarantaine (sans supprimer) les fichiers non references,
        laisses par une publication interrompue. Retourne les chemins deplaces."""
        import shutil
        from datetime import datetime, timezone
        moved = []
        with interprocess_lock(self.index_path):
            referenced = set()
            for e in self.load_index()["reports"]:
                for k in ("path", "dossier_path"):
                    if e.get(k):
                        referenced.add(os.path.realpath(os.path.join(self.root, e[k])))
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            for sub in ("reports", "dossiers"):
                base = os.path.join(self.root, sub)
                if not os.path.isdir(base):
                    continue
                for dp, _, fns in os.walk(base):
                    for fn in fns:
                        p = os.path.realpath(os.path.join(dp, fn))
                        if p not in referenced:
                            rel = os.path.relpath(p, os.path.realpath(self.root))
                            dest = os.path.join(self.root, "quarantine", stamp, rel)
                            os.makedirs(os.path.dirname(dest), exist_ok=True)
                            shutil.move(p, dest)
                            moved.append(rel.replace(os.sep, "/"))
        return moved

    # Champs de l'index recalculables depuis le fichier publie.
    META = {"title": lambda r: r["subject"]["title"], "market": lambda r: r["subject"]["market"],
            "region": lambda r: r["subject"]["region"], "created_at": lambda r: r["created_at"],
            "production_status": lambda r: r["production_status"], "simulated": lambda r: r["simulated"],
            "edge_decision": lambda r: r["decisions"]["edge_decision"]["decision"],
            "data_as_of": lambda r: r["data_as_of"]}

    def fingerprint(self):
        """Empreinte de l'ensemble publie (id, version, empreinte de contenu).
        A CONSERVER HORS DU DEPOT (racine de confiance externe) apres chaque
        publication legitime : c'est la seule facon de detecter une reecriture
        coherente de la derniere version ou une suppression complete."""
        idx = self.load_index()
        rows = sorted((e["report_id"], e["report_version"], e["content_sha256"]) for e in idx["reports"])
        return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()

    def verify(self, expected_fingerprint=None):
        """Anomalies d'integrite (vide = aucune anomalie DETECTABLE).
        Sans `expected_fingerprint`, une reecriture coherente de la DERNIERE
        version (fichier + index) n'est pas detectable : voir EDGE_INTELLIGENCE.md."""
        problems = []
        try:
            idx = self.load_index()
            entries = idx["reports"]
        except (ValueError, KeyError, TypeError) as e:
            return [f"index illisible : {type(e).__name__}"]
        root = os.path.realpath(self.root)
        seen, versions, contents, referenced = set(), {}, {}, set()
        for e in entries:
            key = (e.get("report_id"), e.get("report_version"))
            tag = f"{key[0]} v{key[1]}"
            if key in seen:
                problems.append(f"{tag} : doublon dans l'index")
                continue
            seen.add(key)
            versions.setdefault(key[0], []).append(key[1])
            rel = str(e.get("path", ""))
            full = os.path.realpath(os.path.join(self.root, rel))
            if not full.startswith(root + os.sep):
                problems.append(f"{tag} : chemin hors du stockage ({rel!r})")
                continue
            expected = f"reports/{key[0]}/v{key[1]:04d}.json"
            if rel != expected:
                problems.append(f"{tag} : identite incoherente (chemin {rel!r} au lieu de {expected!r})")
            referenced.add(full)
            if e.get("dossier_path"):
                dfull = os.path.realpath(os.path.join(self.root, e["dossier_path"]))
                referenced.add(dfull)
                if not dfull.startswith(root + os.sep) or not os.path.exists(dfull):
                    problems.append(f"{tag} : dossier d'enquete absent")
                else:
                    with open(dfull, "rb") as f:
                        dbytes = f.read()
                    if hashlib.sha256(dbytes).hexdigest() != e.get("dossier_sha256"):
                        problems.append(f"{tag} : dossier d'enquete modifie apres publication")
                    else:
                        try:
                            if json.loads(dbytes).get("report_sha256") != e.get("content_sha256"):
                                problems.append(f"{tag} : dossier ne correspondant pas au rapport")
                        except ValueError:
                            problems.append(f"{tag} : dossier illisible")
            if not os.path.exists(full):
                problems.append(f"{tag} : fichier absent")
                continue
            try:
                with open(full, encoding="utf-8") as f:
                    rep = json.load(f)
            except ValueError:
                problems.append(f"{tag} : fichier illisible")
                continue
            sha = content_sha256(rep)
            contents[key] = (sha, rep)
            if sha != e.get("content_sha256"):
                problems.append(f"{tag} : contenu modifie apres publication")
            if (rep.get("report_id"), rep.get("report_version")) != key:
                problems.append(f"{tag} : identite du fichier differente de l'entree d'index")
                continue
            try:
                for field, get in self.META.items():
                    if field in e and e[field] != get(rep):
                        problems.append(f"{tag} : metadonnee d'index '{field}' differente du rapport")
                a = assess(rep)
                for field in ("verification_level", "label"):
                    if field in e and e[field] != a[field]:
                        problems.append(f"{tag} : metadonnee d'index '{field}' differente du niveau recalcule")
            except (KeyError, TypeError):
                problems.append(f"{tag} : rapport structurellement invalide")
        for rid, vs in versions.items():
            if sorted(vs) != list(range(1, len(vs) + 1)):
                problems.append(f"{rid} : lacune dans les versions {sorted(vs)}")
        for (rid, ver), (sha, rep) in contents.items():
            if ver > 1 and (rid, ver - 1) in contents:
                sup = (rep.get("supersedes") or {}).get("content_sha256")
                if sup != contents[(rid, ver - 1)][0]:
                    problems.append(f"{rid} v{ver} : chaine rompue (v{ver - 1} ne correspond plus a l'empreinte citee)")
        for rdir in (os.path.join(self.root, "reports"), os.path.join(self.root, "dossiers")):
            if not os.path.isdir(rdir):
                continue
            for dp, _, fns in os.walk(rdir):
                for fn in fns:
                    p = os.path.realpath(os.path.join(dp, fn))
                    if p not in referenced:
                        problems.append(f"fichier non reference par l'index : {os.path.relpath(p, root)}")
        if expected_fingerprint is not None and expected_fingerprint != self.fingerprint():
            problems.append("empreinte globale differente de l'ancre externe (reecriture ou suppression)")
        return problems


def next_version(previous, changes=None, corrections=None, conclusion_changes=None, **updates):
    """Prepare une version corrigee : la precedente reste intacte et
    referencee par son empreinte. Les motifs sont obligatoires."""
    import copy
    new = copy.deepcopy(previous)
    for k, v in updates.items():
        new[k] = v
    sha = content_sha256(previous)
    new["report_version"] = previous["report_version"] + 1
    new["supersedes"] = {"report_id": previous["report_id"], "report_version": previous["report_version"],
                         "content_sha256": sha}
    h = new["history"]
    h["previous_versions"] = previous["history"]["previous_versions"] + [
        {"report_version": previous["report_version"], "content_sha256": sha}]
    h["changes"] = list(changes or [])
    h["corrections"] = list(corrections or [])
    h["conclusion_changes"] = list(conclusion_changes or [])
    return new
