import re
import requests

# URL de la page LEGO 75639 Going Merry sur Cdiscount
TEST_URL = "https://www.cdiscount.com/juniors/lego-one-piece-75639-le-bateau-pirate-vogue-merry-jeu-de-construction/f-121510501-75639.html"

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/122.0.0.0 Safari=0./537.936"),
    "Accept": "text/html,,*application/xhtml+xml,application/xml;q/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

print("=== Diagnostic Cdiscount ===", flush=True)
print(f"URL : {TEST_URL}", flush=True)

try:
    r = requests.get(TEST_URL, headers=HEADERS, timeout=30)
    print(f"[1] HTTP {r.status_code}", flush=True)
    print(f"    Content-Type : {r.headers.get('Content-Type')}", flush=True)
    print(f"    Content-Length : {len(r.text)} bytes", flush=True)
    print(f"    Server : {r.headers.get('Server')}", flush=True)

    # Verifier si DataDome a bloque
    body_lower = r.text.lower()
    if "datadome" in body_lower:
        print(f"[2] DataDome detecte dans la page (blocage probable)", flush=True)
    if "captcha" in body_lower:
        print(f"[2] CAPTCHA detecte (blocage probable)", flush=True)
    if "access denied" in body_lower or "acces refuse" in body_lower:
        print(f"[2] Message 'access denied' detecte", flush=True)

    # Chercher un prix dans le HTML
    print(f"\n[3] Recherche de prix dans le HTML...", flush=True)
    # Pattern principal : prix en EUR avec virgule
    patterns = [
        r'"price"\s*:\s*"?(\d+[.,]\d{2})',
        r'itemprop="price"\s+content="(\d+[.,]\d{2})"',
        r'<meta\s+property="product:price:amount"\s+content="(\d+[.,]\d{2})"',
        r'(\d+)\s*€\s*(\d{2})',
    ]
    for i, pat in enumerate(patterns, 1):
        matches = re.findall(pat, r.text)
        if matches:
            print(f"    Pattern {i} : {matches[:5]}", flush=True)
        else:
            print(f"    Pattern {i} : aucun match", flush=True)

    # Afficher un extrait pour debug
    print(f"\n[4] Extrait du HTML (300 premiers caracteres) :", flush=True)
    print(r.text[:300], flush=True)

except Exception as e:
    print(f"ERREUR : {e}", flush=True)

print("\n=== Fin diagnostic ===", flush=True)