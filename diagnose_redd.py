import sys

print("=== Diagnostic package redd ===", flush=True)

# 1. Le paquet est-il importable ?
try:
    import redd
    print(f"[1] import redd OK, chemin : {redd.__file__}", flush=True)
except ImportError as e:
    print(f"[1] import redd ECHEC : {e}", flush=True)
    sys.exit(1)

# 2. Quels sont ses attributs publics ?
attrs = [a for a in dir(redd) if not a.startswith("_")]
print(f"[2] attributs publics : {attrs}", flush=True)

# 3. Quelques attributs cles en detail
for name in attrs:
    try:
        obj = getattr(redd, name)
        print(f"    - {name} : {type(obj).__name__}", flush=True)
    except Exception as e:
        print(f"    - {name} : erreur {e}", flush=True)

# 4. Version
ver = getattr(redd, "__version__", "inconnue")
print(f"[3] version : {ver}", flush=True)

# 5. Essai d'instanciation si une classe "Redd" ou similaire existe
for cls_name in ["Redd", "ReddClient", "Client", "Reddit"]:
    if hasattr(redd, cls_name):
        print(f"[4] classe trouvee : {cls_name}", flush=True)
        try:
            cls = getattr(redd, cls_name)
            methods = [m for m in dir(cls) if not m.startswith("_")]
            print(f"    methodes : {methods[:20]}", flush=True)
        except Exception as e:
            print(f"    erreur inspection : {e}", flush=True)
        break
else:
    print("[4] aucune classe connue trouvee (Redd, ReddClient, Client, Reddit)", flush=True)

print("=== Fin diagnostic ===", flush=True)