import os, sys, json, requests

def log(msg):
    print(msg, flush=True)

TOKEN = os.environ.get("APIFY_TOKEN")
if not TOKEN:
    log("ERREUR: APIFY_TOKEN absent")
    sys.exit(1)

log(f"Token OK : {TOKEN[:15]}...")

# Acteurs a tester, avec des payloads adaptes a leur schema connu
ACTORS = [
    {
        "id": "unfenced-group~cardmarket-scraper",
        "payloads": [
            {"game": "onepiece", "searchQuery": "OP-18", "productType": "sealed"},
            {"game": "lorcana", "searchQuery": "Hyperia City", "productType": "sealed"},
        ],
    },
    {
        "id": "lowlanddata~cardmarket-deal-finder",
        "payloads": [
            {"game": "onepiece", "searchQuery": "OP-18"},
            {"game": "lorcana", "searchQuery": "Hyperia City"},
        ],
    },
]

for actor in ACTORS:
    log(f"\n{'='*60}")
    log(f"TEST : {actor['id']}")
    log(f"{'='*60}")

    for p in actor["payloads"]:
        log(f"\n--- Payload : {json.dumps(p)} ---")
        try:
            r = requests.post(
                f"https://api.apify.com/v2/acts/{actor['id']}"
                f"/run-sync-get-dataset-items?token={TOKEN}",
                json=p,
                timeout=300
            )
            log(f"HTTP {r.status_code}")
            if r.status_code in (200, 201):
                items = r.json()
                log(f"Items retournes : {len(items)}")
                if items:
                    log(f"Cles du premier item :")
                    for k in items[0].keys():
                        log(f"  - {k} : {str(items[0][k])[:100]}")
                    log(">>> ACTEUR + PAYLOAD QUI FONCTIONNENT <<<")
                    break
                else:
                    log("Aucun item retourne (payload accepte mais vide)")
            else:
                log(f"Reponse : {r.text[:300]}")
        except Exception as e:
            log(f"Exception : {e}")

log("\n--- Diagnostic Cardmarket 2 termine ---")