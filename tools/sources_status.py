"""Etat des acces aux sources : python -m tools.sources_status
N'affiche jamais la valeur d'un identifiant, seulement sa presence."""
from discovery.access import access_status, load_registry


def main():
    reg = load_registry()
    for name, s in reg.items():
        st = access_status(name, reg)
        flag = "UTILISABLE" if st["usable"] else "BLOQUEE"
        print(f"{name:<18} {flag:<11} {'payante' if s.get('paid') else 'gratuite':<9} "
              f"preuves={','.join(s['evidence'])}")
        if not st["usable"]:
            print(f"{'':<18} -> {st['reason']}")
            print(f"{'':<18} -> a verifier : {s['license_required']} ({s.get('terms_url')})")


if __name__ == "__main__":
    main()
