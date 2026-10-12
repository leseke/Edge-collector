import re
import requests

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/122.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Produits test : LEGO 75639 Going Merry
TARGETS = [
    {
        "name": "Fnac",
        "url": "https://www.fnac.com/mp50488320/LEGO-One-Piece-Le-Bateau-Pirate-Vogue-Merry-Jeu-de-construction-pour-enfant-de-9-ans-75639",
    },
    {
        "name": "JouetClub",
        "url": "https://www.jouetclub.fr/lego-one-piece-75639-le-bateau-pirate-vogue-merry/",
    },
    {
        "name": "LaGrandeRecre",
        "url": "https://www.lagranderecre.fr/lego-one-piece-75639-le-bateau-pirate-vogue-merry.html",
    },
    {
        "name": "RueDuCommerce",
        "url": "https://www.rueducommerce.fr/produit/lego-one-piece-75639-le-bateau-pirate-vogue-merry-218495969",
    },
    {
        "name": "Cdiscount",
        "url": "https://www.cdiscount.com/juniors/lego-one-piece-75639-le-bateau-pirate-vogue-merry-jeu-de-construction/f-121510501-75639.html",
    },
]

print("=== Diagnostic retailers FR ===", flush=True)

for target in TARGETS:
    print(f"\n{'='*50}", flush=True)
    print(f"[{target['name']}]", flush=True)
    print(f"{'='*50}", flush=True)

    try:
        r = requests.get(target["url"], headers=HEADERS, timeout=30,
                         allow_redirects=True)
        print(f"HTTP {r.status_code} | size {len(r.text)} bytes | "
              f"server {r.headers.get('Server', '?')} | "
              f"final url {r.url[:80]}", flush=True)

        body_lower = r.text.lower()

        # Detecter les protections
        flags = []
        if "cloudflare" in body_lower: flags.append("cloudflare")
        if "datadome" in body_lower: flags.append("datadome")
        if "captcha" in body_lower: flags.append("captcha")
        if "access denied" in body_lower: flags.append("access-denied")
        if "just a moment" in body_lower: flags.append("cf-challenge")
        if len(r.text) < 30000: flags.append("page-trop-courte")

        if flags:
            print(f"  ⚠️ flags : {', '.join(flags)}", flush=True)
        else:
            print(f"  ✅ pas de flag de blocage evident", flush=True)

        # Chercher un prix
        price_patterns = [
            (r'"price"\s*:\s*"?(\d+[.,]\d{2})', "json-price"),
            (r'itemprop="price"\s+content="(\d+[.,]\d{2})"', "microdata"),
            (r'<meta\s+property="product:price:amount"\s+content="(\d+[.,]\d{2})"', "og-meta"),
            (r'(\d{2,3}[.,]\d{2})\s*€', "eur-text"),
            (r'(\d{2,3})\s*€\s*(\d{2})', "eur-split"),
        ]
        found_prices = []
        for pat, label in price_patterns:
            matches = re.findall(pat, r.text)
            if matches:
                found_prices.append(f"{label}={matches[:3]}")
        if found_prices:
            print(f"  💰 prix trouves : {found_prices}", flush=True)
        else:
            print(f"  ❌ aucun prix detecte", flush=True)

    except Exception as e:
        print(f"  ERREUR : {e}", flush=True)

print("\n=== Fin diagnostic ===", flush=True)