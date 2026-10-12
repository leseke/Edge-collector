import inspect
from redd import Redd

print("=== Signatures des methodes Redd ===", flush=True)

for name in ["search_subreddit", "get_subreddit_posts", "search"]:
    try:
        method = getattr(Redd, name)
        sig = inspect.signature(method)
        print(f"\n[{name}]", flush=True)
        print(f"  signature : {sig}", flush=True)
        doc = (method.__doc__ or "").strip().split("\n")[0]
        print(f"  doc : {doc}", flush=True)
    except Exception as e:
        print(f"[{name}] erreur : {e}", flush=True)

print("\n=== Constructeur de Redd ===", flush=True)
try:
    init_sig = inspect.signature(Redd.__init__)
    print(f"Redd.__init__ {init_sig}", flush=True)
except Exception as e:
    print(f"erreur : {e}", flush=True)

print("\n=== Test reel sur r/lego ===", flush=True)
try:
    r = Redd()
    print("[ok] instance creee", flush=True)

    # Tentative 1 : get_subreddit_posts simple
    try:
        posts = r.get_subreddit_posts("lego", limit=5)
        posts = list(posts)
        print(f"[tentative 1] get_subreddit_posts('lego', limit=5) -> {len(posts)} posts", flush=True)
        if posts:
            first = posts[0]
            print(f"  type : {type(first).__name__}", flush=True)
            print(f"  attrs : {[a for a in dir(first) if not a.startswith('_')][:15]}", flush=True)
    except Exception as e:
        print(f"[tentative 1] echoue : {e}", flush=True)

    r.close()
except Exception as e:
    print(f"[erreur globale] {e}", flush=True)

print("\n=== Fin ===", flush=True)