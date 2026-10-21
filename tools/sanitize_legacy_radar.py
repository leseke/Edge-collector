"""Assainit un radar.json V3 (publie avec des donnees financieres).

Par defaut : SIMULATION (liste les champs prives, ne modifie rien).
--apply :
  1. sauvegarde l'original INTACT dans private/legacy/ (ignore par git) ;
  2. reecrit radar.json au format public V4 : sans config, sans montant,
     sans allocation, statut recalcule (un radar 100 % ERROR devient FAILED,
     plus jamais "CASH").
Aucune donnee de marche n'est supprimee ; seules les cles privees le sont.
"""
import argparse
import json
import os

from edge_engine import (FAILURE_DECISIONS, SIGNAL_DECISIONS, public_policy,
                         public_product_view, public_summary, summarize,
                         assert_no_private_leak)
from edge_io import atomic_write_json
from tools.check_public_files import check_file


def migrate(old):
    products = []
    for p in old.get("products", []):
        q = public_product_view(p)
        q.setdefault("opportunity_alert", p.get("decision") in SIGNAL_DECISIONS)
        if p.get("decision") in FAILURE_DECISIONS:
            q.setdefault("failure_reason", "inconnue (radar V3 migre)")
        products.append(q)
    summary = public_summary(summarize(products, {}))
    new = {
        "schema_version": 4,
        "migrated_from": {"schema": "v3", "generated_at": old.get("generated_at"),
                          "previous_decision": (old.get("summary") or {}).get("decision")},
        "generated_at": old.get("generated_at"),
        "policy": public_policy(old.get("config") or {}),
        "summary": summary,
        "products": products,
        "trends": old.get("trends", []),
        "reddit": old.get("reddit", []),
        "scavio_offers": old.get("scavio_offers", []),
    }
    assert_no_private_leak(new)
    return new


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--radar", default="radar.json")
    ap.add_argument("--backup-dir", default=os.path.join("private", "legacy"))
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    problems = check_file(a.radar)
    print(f"{len(problems)} champ(s) prive(s) dans {a.radar}")
    for p in problems:
        print("  -", p)
    if not problems:
        print("Rien a faire.")
        return 0
    with open(a.radar, encoding="utf-8") as f:
        old = json.load(f)
    new = migrate(old)
    print(f"Statut publie : {(old.get('summary') or {}).get('decision')} -> {new['summary']['decision']}")
    if not a.apply:
        print("Simulation : aucun fichier modifie. Relancer avec --apply.")
        return 0
    stamp = (old.get("generated_at") or "unknown").replace(":", "").replace("+", "_")
    backup = os.path.join(a.backup_dir, f"radar_v3_{stamp}.json")
    if os.path.exists(backup):
        raise SystemExit(f"sauvegarde deja presente, abandon : {backup}")
    os.makedirs(a.backup_dir, exist_ok=True)
    with open(a.radar, "rb") as src, open(backup, "wb") as dst:
        dst.write(src.read())
    atomic_write_json(a.radar, new)
    left = check_file(a.radar)
    print(f"Sauvegarde : {backup}\nControle apres assainissement : {len(left)} probleme(s)")
    return 1 if left else 0


if __name__ == "__main__":
    main()
