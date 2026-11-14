"""Garde-fou avant publication : refuse tout fichier public contenant
une cle financiere privee ou un secret reconnaissable.

python -m tools.check_public_files                 # sorties generees (radar.json, data/)
python -m tools.check_public_files config.json     # n'importe quel chemin
Code retour 1 si un probleme est trouve.
"""
import json
import os
import re
import sys

from edge_engine import PRIVATE_KEYS, PRIVATE_PRODUCT_KEYS

DEFAULT_PATHS = ["radar.json", "data"]
SECRET_RE = [
    re.compile(r"token=[A-Za-z0-9_\-]{8,}"),
    re.compile(r"bot\d{6,}:[A-Za-z0-9_\-]{20,}"),
    re.compile(r"apify_api_[A-Za-z0-9]{10,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{12,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),                       # cle API OpenAI
    re.compile(r"OPENAI_API_KEY\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{8,}"),
]
FORBIDDEN = PRIVATE_KEYS | PRIVATE_PRODUCT_KEYS | {"financement"}
# Une autorisation de depense n'a rien a faire dans un fichier public,
# sauf modele *.example avec authorized=false (verifie a part).
FORBIDDEN_IF_TRUTHY = {"authorized"}


def _walk_keys(obj, path, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in FORBIDDEN or (k in FORBIDDEN_IF_TRUTHY and v is True):
                out.append(f"{path}.{k}")
            _walk_keys(v, f"{path}.{k}", out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk_keys(v, f"{path}[{i}]", out)


def _nonzero_private(obj):
    """Pour les fichiers *.example : seules les valeurs non nulles comptent."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in FORBIDDEN and v not in (0, 0.0, None, "", [], {}, [0, 0]):
                out.append(k)
            if k in FORBIDDEN_IF_TRUTHY and v is True:
                out.append(k)
            out += _nonzero_private(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _nonzero_private(v)
    return out


def check_file(path):
    problems = []
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    for pat in SECRET_RE:
        if pat.search(text):
            problems.append(f"{path}: motif de secret ({pat.pattern[:20]}...)")
    records = []
    if path.endswith(".json.example"):
        try:
            return problems + [f"{path}: valeur privee non nulle {k}" for k in _nonzero_private(json.loads(text))]
        except ValueError:
            return problems + [f"{path}: JSON invalide"]
    if path.endswith(".json"):
        try:
            records = [json.loads(text)]
        except ValueError:
            problems.append(f"{path}: JSON invalide")
    elif path.endswith(".jsonl"):
        for n, line in enumerate(text.splitlines(), 1):
            if line.strip():
                try:
                    records.append(json.loads(line))
                except ValueError:
                    problems.append(f"{path}:{n}: ligne JSONL invalide")
    keys = []
    for r in records:
        _walk_keys(r, "$", keys)
    problems += [f"{path}: cle privee {k}" for k in keys]
    return problems


def iter_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for f in sorted(files):
                    if f.endswith((".json", ".jsonl", ".md", ".txt", ".example")):
                        yield os.path.join(root, f)
        elif os.path.exists(p):
            yield p


EXTS = (".json", ".jsonl", ".md", ".txt", ".example", ".yml", ".html", ".py")


def _gitignore_rules(root):
    rules = []
    p = os.path.join(root, ".gitignore")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            rules = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    return rules


def _ignored(rel, rules):
    import fnmatch
    parts = rel.split("/")
    for r in rules:
        r = r.rstrip("/")
        if any(fnmatch.fnmatch(seg, r) for seg in parts) or fnmatch.fnmatch(rel, r):
            return True
    return False


def tracked_files(root="."):
    """Fichiers suivis par git (ce que GitHub et Pages exposent). Sans
    depot git (ex. archive ZIP), repli EXPLICITE sur l'arborescence en
    appliquant .gitignore : le controle n'est jamais saute."""
    import subprocess
    try:
        out = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                             check=True, cwd=root).stdout
        files = out.splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        print("[controle] pas de depot git : repli sur l'arborescence filtree par .gitignore",
              file=sys.stderr)
        rules = _gitignore_rules(root) + [".git"]
        files = []
        for dp, dns, fns in os.walk(root):
            rel_dir = os.path.relpath(dp, root).replace(os.sep, "/")
            dns[:] = [d for d in dns if not _ignored((d if rel_dir == "." else f"{rel_dir}/{d}"), rules)]
            for fn in fns:
                rel = fn if rel_dir == "." else f"{rel_dir}/{fn}"
                if not _ignored(rel, rules):
                    files.append(rel)
    return sorted(f for f in files if f.endswith(EXTS))


def main(argv=None):
    args = list(argv if argv is not None else sys.argv[1:])
    if args == ["--tracked"]:
        args = tracked_files()
        if not args:
            print("AUCUN fichier a controler : echec par prudence")
            return 1
    paths = args or DEFAULT_PATHS
    problems, n = [], 0
    for f in iter_files(paths):
        n += 1
        problems += check_file(f)
    for p in problems:
        print("FUITE :", p)
    print(f"{n} fichier(s) controle(s), {len(problems)} probleme(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
