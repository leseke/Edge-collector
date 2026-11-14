"""Prepare la separation config.json (public) / config.private.json (prive).

Par defaut : SIMULATION. Affiche ce qui serait deplace, ne modifie rien.
--apply : deplace les cles financieres SANS changer leurs valeurs.
Ne cree pas de 'treasury' : ce montant reste une decision de l'utilisateur.
"""
import argparse
import json
import os

from edge_engine import PRIVATE_KEYS
from edge_io import atomic_write_json


def plan(public_cfg, private_cfg):
    move = {k: v for k, v in public_cfg.items() if k in PRIVATE_KEYS}
    conflicts = {k: (v, private_cfg[k]) for k, v in move.items()
                 if k in private_cfg and private_cfg[k] != v}
    new_public = {k: v for k, v in public_cfg.items() if k not in PRIVATE_KEYS}
    new_private = {**move, **private_cfg}  # le prive existant prime
    return move, conflicts, new_public, new_private


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--public", default="config.json")
    ap.add_argument("--private", default="config.private.json")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    with open(a.public, encoding="utf-8") as f:
        pub = json.load(f)
    priv = {}
    if os.path.exists(a.private):
        with open(a.private, encoding="utf-8") as f:
            priv = json.load(f)
    move, conflicts, new_pub, new_priv = plan(pub, priv)
    print("Cles a deplacer :", sorted(move) or "aucune")
    if conflicts:
        print("CONFLITS (valeur privee conservee) :", sorted(conflicts))
    if "treasury" not in new_priv:
        print("ATTENTION : 'treasury' absent -> execution bloquee tant que tu ne le renseignes pas.")
    if not a.apply:
        print("Simulation : aucun fichier modifie. Relancer avec --apply pour appliquer.")
        return 0
    atomic_write_json(a.private, new_priv)  # prive d'abord : rien n'est perdu
    atomic_write_json(a.public, new_pub)
    print(f"Applique : {a.public} nettoye, {a.private} mis a jour.")
    return 0


if __name__ == "__main__":
    main()
