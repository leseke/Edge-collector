import os, sys, json, requests

def log(msg):
    print(msg, flush=True)

TOKEN = os.environ.get("APIFY_TOKEN")
if not TOKEN:
    log("❌ APIFY_TOKEN absent des variables d'environnement")
    sys.exit(1)

log(f"✅ Token présent : {TOKEN[:15]}...")

# 1. Verifier le token
r = requests.get(f"https://api.apify.com/v2/users/me?token={TOKEN}", timeout=30)
log(f"\n[1] GET /users/me -> HTTP {r.status_code}")
if r.status_code == 200:
    data = r.json().get("data", {})
    log(f"    Username : {data.get('username')}")
    log(f"    Plan     : {data.get('plan', {}).get('id', 'unknown')}")
else:
    log(f"    Reponse : {r.text[:300]}")

# 2. Verifier l'acteur qu'on utilise actuellement
ACTOR = "tnodes~ebay-sold-scraper"
r = requests.get(f"https://api.apify.com/v2/acts/{ACTOR}?token={TOKEN}", timeout=30)
log(f"\n[2] GET /acts/{ACTOR} -> HTTP {r.status_code}")
if r.status_code == 200:
    d = r.json().get("data", {})
    log(f"    Nom : {d.get('name')}")
    log(f"    Titre : {d.get('title')}")
else:
    log(f"    ❌ Acteur introuvable ou inaccessible")
    log(f"    Reponse : {r.text[:300]}")

# 3. Chercher l'acteur eBay le plus populaire sur le store
r = requests.get(
    "https://api.apify.com/v2/store?search=ebay+sold&limit=10&token=" + TOKEN,
    timeout=30
)
log(f"\n[3] Recherche acteurs eBay -> HTTP {r.status_code}")
if r.status_code == 200:
    items = r.json().get("data", {}).get("items", [])
    for i, it in enumerate(items[:5], 1):
        log(f"    {i}. {it.get('username')}/{it.get('name')} — "
            f"{it.get('stats', {}).get('totalUsers', '?')} users")
else:
    log(f"    Reponse : {r.text[:300]}")

log("\n--- Diagnostic termine ---")
