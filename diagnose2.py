import os, sys, json, requests

def log(msg):
    print(msg, flush=True)

TOKEN = os.environ.get("APIFY_TOKEN")
if not TOKEN:
    log("ERREUR: APIFY_TOKEN absent")
    sys.exit(1)

ACTORS = [
    "tnodes~ebay-sold-scraper",
    "caffein.dev~ebay-sold-listings",
]

# --- 1. Recuperer le schema d'input de chaque acteur ---
for actor in ACTORS:
    log(f"\n=== Schema input de {actor} ===")
    r = requests.get(
        f"https://api.apify.com/v2/acts/{actor}/input-schema?token={TOKEN}",
        timeout=30
    )
    log(f"HTTP {r.status_code}")
    if r.status_code == 200:
        schema = r.json().get("data", {})
        props = schema.get("properties", {})
        required = schema.get("required", [])
        log(f"Champs requis : {required}")
        for k, v in props.items():
            t = v.get("type", "?")
            d = (v.get("description") or "")[:80]
            log(f"  - {k} ({t}) : {d}")
    else:
        log(f"Erreur : {r.text[:200]}")

# --- 2. Mini-test reel sur caffein.dev (le plus populaire) ---
log(f"\n=== Test reel : caffein.dev/ebay-sold-listings ===")
log("Envoi payload minimal : 3 resultats pour 'LEGO 77073'")

test_payload = {
    "keyword": "LEGO 77073",
    "maxItems": 3,
}

r = requests.post(
    f"https://api.apify.com/v2/acts/caffein.dev~ebay-sold-listings"
    f"/run-sync-get-dataset-items?token={TOKEN}",
    json=test_payload,
    timeout=300
)
log(f"HTTP {r.status_code}")
log(f"Reponse brute (500 premiers caracteres) :")
log(r.text[:500])

if r.status_code in (200, 201):
    try:
        items = r.json()
        log(f"\nNombre d'items retournes : {len(items)}")
        if items:
            log(f"\nPremier item (cles disponibles) :")
            for k, v in items[0].items():
                log(f"  - {k} : {str(v)[:100]}")
    except Exception as e:
        log(f"Erreur parsing JSON : {e}")

log("\n--- Diagnostic 2 termine ---")
