"""Ecritures atomiques et redaction de secrets (partage V4 / Discovery)."""
import json
import os
import re
import tempfile

_SECRET_PATTERNS = [
    re.compile(r"(token=)[^&\s]+", re.I),
    re.compile(r"(bot)\d+:[A-Za-z0-9_-]+"),
    re.compile(r"(Bearer\s+)[A-Za-z0-9._-]+", re.I),
    re.compile(r"((?:api[_-]?key|apikey|secret)[\"'=:\s]+)[A-Za-z0-9._-]{8,}", re.I),
]


def redact(text):
    """Masque les secrets reconnaissables dans un message d'erreur/log."""
    s = str(text)
    for pat in _SECRET_PATTERNS:
        s = pat.sub(lambda m: m.group(1) + "***", s)
    for env in ("APIFY_TOKEN", "SCAVIO_API_KEY", "TELEGRAM_TOKEN"):
        v = os.environ.get(env)
        if v and len(v) >= 6:
            s = s.replace(v, "***")
    return s[:500]


def atomic_write_json(path, data):
    """Ecrit via fichier temporaire + os.replace : jamais de JSON tronque."""
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def append_jsonl(path, record):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())
