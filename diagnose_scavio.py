import os
import inspect

print("=== Diagnostic Scavio SDK ===", flush=True)

# 1. Le package est-il installable ?
try:
    import scavio
    print(f"[1] import scavio OK, chemin : {scavio.__file__}", flush=True)
except ImportError as e:
    print(f"[1] import scavio ECHEC : {e}", flush=True)
    raise SystemExit(1)

# 2. Attributs publics
attrs = [a for a in dir(scavio) if not a.startswith("_")]
print(f"[2] attributs publics : {attrs}", flush=True)

# 3. Version
ver = getattr(scavio, "__version__", "inconnue")
print(f"[3] version : {ver}", flush=True)

# 4. Chercher la classe client
for cls_name in ["ScavioClient", "Scavio", "Client"]:
    if hasattr(scavio, cls_name):
        cls = getattr(scavio, cls_name)
        print(f"\n[4] classe trouvee : {cls_name}", flush=True)
        try:
            sig = inspect.signature(cls.__init__)
            print(f"    __init__ {sig}", flush=True)
        except Exception as e:
            print(f"    erreur signature : {e}", flush=True)

        methods = [m for m in dir(cls) if not m.startswith("_")]
        print(f"    methodes : {methods[:30]}", flush=True)

        # Inspecter la méthode shopping si elle existe
        for m_name in ["shopping", "google", "search"]:
            if hasattr(cls, m_name):
                obj = getattr(cls, m_name)
                print(f"    - {m_name} : {type(obj).__name__}", flush=True)
                try:
                    m_sig = inspect.signature(obj) if callable(obj) else "n/a"
                    print(f"      signature : {m_sig}", flush=True)
                except Exception:
                    pass
        break

# 5. Verifier la presence de la cle API
key = os.environ.get("SCAVIO_API_KEY")
if key:
    print(f"\n[5] SCAVIO_API_KEY present : {key[:10]}... (longueur {len(key)})", flush=True)
    # Verifier les problemes courants
    if key != key.strip():
        print("    ⚠️ espaces en debut/fin de cle", flush=True)
    if key.startswith("sk_test_") or key.startswith("test_"):
        print("    ⚠️ cle de test detectee", flush=True)
    if key.startswith("sk_live_"):
        print("    ✅ cle live detectee", flush=True)
else:
    print("[5] SCAVIO_API_KEY absent", flush=True)

# 6. Variables d'environnement que le SDK cherche
print("\n[6] Recherche de patterns d'env vars dans le code source", flush=True)
try:
    import scavio
    src_files = []
    base = os.path.dirname(scavio.__file__)
    for root, dirs, files in os.walk(base):
        for f in files:
            if f.endswith(".py"):
                src_files.append(os.path.join(root, f))

    for f in src_files[:5]:
        with open(f) as fh:
            content = fh.read()
            if "SCAVIO" in content or "api_key" in content.lower():
                import re
                patterns = re.findall(r'["\'](SCAVIO_[A-Z_]+)["\']', content)
                if patterns:
                    print(f"    {os.path.basename(f)} : {set(patterns)}", flush=True)
except Exception as e:
    print(f"    erreur inspection : {e}", flush=True)

print("\n=== Fin diagnostic ===", flush=True)