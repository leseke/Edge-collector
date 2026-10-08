import os, sys, json, requests

def log(msg):
    print(msg, flush=True)

TOKEN = os.environ.get("APIFY_TOKEN")
if not TOKEN:
    log("ERREUR: APIFY_TOKEN absent")
    sys.exit(1)

log(f"Token OK : {TOKEN[:15]}...")

ACTORS = [
    "crawloop~cardmarket-listings-scraper",
    "ecomscrape~cardmarket-trend-scraper",
]

# --- 1. Recuperer le schema d'input de chaque acteur ---
for actor in ACTORS:
    log(f"\n{'='*60}")
    log(f"SCHEMA INPUT : {actor}")
    log(f"{'='*60}")
    r = requests.get(
        f"https://api.apify.com/v2/acts/{actor}/input-schema?token={TOKEN}",
        timeout=30
    )
    log(f"HTTP {r.status_code}")
    if r.status_code == 200:
        try:
            schema = r.json().get("data", {})
            props = schema.get("properties", {})
            required = schema.get("required", [])
            log(f"Champs REQUIS : {required}")
            log(f"Tous les champs disponibles :")
            for k, v in props.items():
                t = v.get("type", "?")
                d = (v.get("description") or v.get("title") or "")[:120]
                log(f"  - {k} ({t}) : {d}")
        except Exception as e:
            log(f"Erreur parsing schema : {e}")
            log(r.text[:500])
    else:
        log(f"Erreur : {r.text[:300]}")

# --- 2. Test reel sur crawloop ---
log(f"\n{'='*60}")
log("TEST REEL : crawloop~cardmarket-listings-scraper")
log(f"{'='*60}")

PAYLOADS = [
    {"name": "searchKeywords + maxItems",
     "body": {"searchKeywords": ["Hyperia City booster box"],
              "maxItems": 5}},
    {"name": "searchKeywords seul",
     "body": {"searchKeywords": ["Riftbound Radiance booster box"]}},
    {"name": "keyword + maxResults",
     "body": {"keyword": "One Piece OP-18 booster box",
              "maxResults": 5}},
]

for p in PAYLOADS:
    log(f"\n--- Tentative : {p['name']} ---")
    log(f"Payload : {json.dumps(p['body'])}")
    try:
        r = requests.post(
            f"https://api.apify.com/v2/acts/"
            f"crawloop~cardmarket-listings-scraper"
            f"/run-sync-get-dataset-items?token={TOKEN}",
            json=p["body"],
            timeout=300
        )
        log(f"HTTP {r.status_code}")
        if r.status_code in (200, 201):
            try:
                items = r.json()
                log(f"Items retournes : {len(items)}")
                if items:
                    log(f"Cles du premier item :")
                    for k in items[0].keys():
                        log(f"  - {k} : {str(items[0][k])[:80]}")
                    log(">>> PAYLOAD QUI FONCTIONNE <<<")
                    break
            except Exception as e:
                log(f"Erreur parsing : {e}")
                log(f"Reponse brute : {r.text[:300]}")
        else:
            log(f"Reponse : {r.text[:300]}")
    except Exception as e:
        log(f"Exception : {e}")

log("\n--- Diagnostic Cardmarket termine ---")