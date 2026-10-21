import os
import json
from datetime import datetime, timezone

from connectors.ebay import fetch_sold as fetch_ebay
from connectors.cardmarket import fetch_cardmarket
from connectors.trends_spy import fetch_trends_spy
from connectors.reddit import fetch_reddit
from connectors.scavio import fetch_scavio_offers
from connectors.telegram import send_message, format_alert, send_daily_digest
from storage import init_db, insert_snapshots
from edge_engine import (load_config, load_portfolio, decide, capital_state,
                         summarize, public_policy, public_product_view,
                         public_summary, assert_no_private_leak)
from edge_io import atomic_write_json, redact

USD_TO_EUR = 0.92


WATCHLIST = [
    {
        "id": "lego_77073",
        "name": "LEGO 77073 Fortnite Battle Bus",
        "emoji": "🚌",
        "image_url": "https://img.bricklink.com/ItemImage/SN/0/77073-1.png",
        "source": "ebay",
        "category": "flip",
        "query": "LEGO 77073",
        "must_all": ["77073"],
        "must_any": ["lego", "fortnite", "battle bus"],
        "target_buy": 60,
        "target_strong_buy": 50,
        "thesis": "Licence Fortnite extremement populaire aupres du public jeune adulte, set LEGO dont le retrait est souvent annonce peu de temps a l'avance.",
        "counter_thesis": "Aucun catalyseur date confirme. La production LEGO peut etre prolongee si les ventes restent fortes.",
        "invalidation": "Si LEGO prolonge au-dela de 2027, la these est morte. Si le prix median depasse 100 EUR, la fenetre est fermee.",
    },
    {
        "id": "lego_75639",
        "name": "LEGO 75639 Going Merry One Piece",
        "emoji": "⛵",
        "image_url": "https://img.bricklink.com/ItemImage/SN/0/75639-1.png",
        "source": "ebay",
        "category": "future_classic",
        "query": "LEGO 75639",
        "must_all": ["75639"],
        "must_any": ["lego", "one piece", "going merry"],
        "target_buy": 90,
        "target_strong_buy": 80,
        "thesis": "Premier set LEGO base sur One Piece, licence culte au Japon et en forte croissance en Europe.",
        "counter_thesis": "Le prix actuel du marche est deja eleve. La production pourrait durer plusieurs annees.",
        "invalidation": "Si LEGO sort une reedition amelioree du Going Merry, l'original perd sa valeur historique.",
    },
    {
        "id": "lego_21371",
        "name": "LEGO 21371 Wallace & Gromit",
        "emoji": "🧀",
        "image_url": "https://img.bricklink.com/ItemImage/SN/0/21371-1.png",
        "source": "ebay",
        "category": "future_classic",
        "query": "LEGO 21371",
        "must_all": ["21371"],
        "must_any": ["lego", "wallace", "gromit"],
        "target_buy": 85,
        "target_strong_buy": 70,
        "thesis": "Licence culte depuis les annees quatre-vingt-dix, public adulte nostalgique, format LEGO Ideas a tirage initial limite.",
        "counter_thesis": "Le marche europeen peut etre moins demande que le marche americain pour cette licence.",
        "invalidation": "Si LEGO prolonge la production au-dela de 2027, la these de rarete s'effondre.",
    },
    {
        "id": "lorcana_hyperia_box",
        "name": "Lorcana Hyperia City Booster Box",
        "emoji": "✨",
        "image_url": "",
        "source": "cardmarket",
        "category": "flip",
        "game": "lorcana",
        "search_query": "Hyperia City",
        "must_all": ["hyperia"],
        "must_any": ["booster box", "display"],
        "must_not": ["case", "sleeve", "playmat", "bundle", "single"],
        "target_buy": 100,
        "target_strong_buy": 85,
        "thesis": "Sortie officielle en octobre 2026, Disney et Pixar se croisent dans un set Lorcana.",
        "counter_thesis": "La sortie est trop recente pour avoir un historique de ventes secondaires fiables.",
        "invalidation": "Si Disney annonce une reimpression massive dans les six mois, la these de rarete est morte.",
    },
    {
        "id": "riftbound_radiance_box",
        "name": "Riftbound Radiance Booster Box",
        "emoji": "⚔️",
        "image_url": "",
        "source": "cardmarket",
        "category": "flip",
        "game": "riftbound",
        "search_query": "Radiance",
        "must_all": ["radiance"],
        "must_any": ["booster box", "display"],
        "must_not": ["case", "sleeve", "playmat", "bundle"],
        "target_buy": 110,
        "target_strong_buy": 100,
        "thesis": "Sortie en octobre 2026, nouveau jeu de Riot Games qui capitalise sur l'univers de League of Legends.",
        "counter_thesis": "Riot a un historique de reimpressions agressives quand un produit marche.",
        "invalidation": "Si Riot annonce une seconde impression dans les six mois, la these de rarete est morte.",
    },
]


TRENDS_POOL = [
    {"keyword": "LEGO Fortnite", "id": "trends_lego_fortnite"},
    {"keyword": "LEGO Going Merry", "id": "trends_lego_goingmerry"},
    {"keyword": "LEGO Wallace Gromit", "id": "trends_lego_wallace"},
    {"keyword": "Lorcana Hyperia", "id": "trends_lorcana_hyperia"},
    {"keyword": "Riftbound", "id": "trends_riftbound"},
]


REDDIT_POOL = [
    {"subreddit": "lego", "query": "Going Merry", "id": "reddit_lego_75639"},
    {"subreddit": "Lorcana", "query": "Hyperia", "id": "reddit_lorcana_hyperia"},
    {"subreddit": "Riftbound", "query": "Radiance", "id": "reddit_riftbound"},
]


SCAVIO_WATCH = [
    {"query": "LEGO 75639 Going Merry", "id": "scavio_lego_75639"},
    {"query": "LEGO 77073 Fortnite", "id": "scavio_lego_77073"},
    {"query": "LEGO 21371 Wallace Gromit", "id": "scavio_lego_21371"},
    {"query": "Lorcana Hyperia City booster box", "id": "scavio_lorcana_hyperia"},
    {"query": "Riftbound Radiance booster box", "id": "scavio_riftbound_radiance"},
]


def _get_run_number():
    try:
        return int(os.environ.get("GITHUB_RUN_NUMBER", "0"))
    except (ValueError, TypeError):
        return 0


def _get_trends_watch():
    run_n = _get_run_number()
    start = run_n % len(TRENDS_POOL)
    return [TRENDS_POOL[start]]


def _get_reddit_watch():
    run_n = _get_run_number()
    start = (run_n + 1) % len(REDDIT_POOL)
    return [REDDIT_POOL[start]]


def _is_enabled(config, source_name):
    return config.get("enabled_sources", {}).get(source_name, True)


def fetch_one(item):
    if item["source"] == "ebay":
        return fetch_ebay(item["query"],
                          must_all=item.get("must_all"),
                          must_any=item.get("must_any"),
                          count=100)
    if item["source"] == "cardmarket":
        return fetch_cardmarket(game=item["game"],
                                search_query=item["search_query"],
                                must_all=item.get("must_all"),
                                must_any=item.get("must_any"),
                                must_not=item.get("must_not"))
    raise ValueError(f"source inconnue : {item['source']}")


PRIVATE_OUTPUT = os.path.join("private", "run_private.json")


def _base_product(item):
    return {
        "id": item["id"], "name": item["name"],
        "emoji": item.get("emoji", "?"),
        "image_url": item.get("image_url", ""),
        "source": item["source"],
        "target_buy": item.get("target_buy"),
        "target_strong_buy": item.get("target_strong_buy"),
        "categorie": item.get("category", "flip").upper(),
        "thesis": item.get("thesis", ""),
        "counter_thesis": item.get("counter_thesis", ""),
        "invalidation": item.get("invalidation", ""),
    }


def _failure_product(item, decision, reason):
    p = _base_product(item)
    p.update({"decision": decision, "price_eur": None, "ecart_pct": None,
              "cycle_num": 0, "cycle_label": "Inconnu",
              "opportunity_alert": False, "execution_ready": False,
              "allocation_eur": [0, 0], "failure_reason": reason,
              "price_basis": None})
    return p


def scavio_id_for(item_id):
    return "scavio_" + item_id


def match_verified_offer(item, scavio_entry):
    """Meilleure offre retail dont le titre contient tous les must_all.

    Une offre sans lien https ou sans prix EUR n'est pas verifiable.
    """
    if not scavio_entry:
        return None
    must_all = [m.lower() for m in item.get("must_all", [])]
    best = None
    for o in scavio_entry.get("offers", []):
        title = (o.get("title") or "").lower()
        link = o.get("product_link") or ""
        price = o.get("price_eur")
        if not title or not link.startswith("https://") or not price:
            continue
        if not all(w in title for w in must_all):
            continue
        if best is None or price < best["price_eur"]:
            best = {"price_eur": price, "url": link, "seller": o.get("seller"),
                    "title": o.get("title")}
    return best


def evaluate_product(item, snap, config, offer=None):
    """Snapshot -> produit radar complet (prive). Pur, testable hors reseau."""
    if not snap:
        return _failure_product(item, "NO_DATA", "aucun resultat")
    median = snap.get("sold_price_median")
    if median is None:
        return _failure_product(item, "NO_DATA", "prix median absent")
    prix_eur = median * USD_TO_EUR if item["source"] == "ebay" else median
    d = decide(item, prix_eur, snap, config, offer=offer)
    p = _base_product(item)
    p.update({
        "decision": d["decision"],
        "message": d["message"],
        "price_eur": round(prix_eur, 2),
        # Base du prix : vente conclue (eBay) ou tendance marche (Cardmarket).
        # Ce n'est PAS une offre achetable.
        "price_basis": "SOLD_MEDIAN" if item["source"] == "ebay" else "MARKET_TREND",
        "median": median,
        "currency_src": snap.get("currency"),
        "low": snap.get("lowest_ask"),
        "n": snap.get("_n_matched") or snap.get("_n_filtered"),
        "ecart_pct": d["ecart_pct"],
        "cycle_num": d["cycle_num"],
        "cycle_label": d["cycle_label"],
        "opportunity_alert": d["opportunity_alert"],
        "verified_offer": offer,
        "allocation_eur": d["allocation_eur"],
        "capital_sufficient": d["capital_sufficient"],
        "allocation_sufficient": d["allocation_sufficient"],
        "execution_ready": d["execution_ready"],
        "execution_blockers": d["execution_blockers"],
    })
    return p


def build_outputs(products, config, sources_failed, trends_signals,
                  reddit_signals, scavio_offers, generated_at):
    """Construit (radar public, rapport prive). Leve si fuite ou compteurs
    incoherents : mieux vaut aucun radar qu'un radar faux."""
    summary = summarize(products, config, sources_failed)
    state = capital_state(config)
    radar = {
        "schema_version": 4,
        "generated_at": generated_at,
        "policy": public_policy(config),
        "summary": public_summary(summary),
        "products": [public_product_view(p) for p in products],
        "trends": trends_signals,
        "reddit": reddit_signals,
        "scavio_offers": scavio_offers,
    }
    assert_no_private_leak(radar)
    private = {
        "generated_at": generated_at,
        "capital": state,
        "summary": summary,
        "funding": [{k: p.get(k) for k in (
            "id", "decision", "opportunity_alert", "allocation_eur",
            "capital_sufficient", "allocation_sufficient",
            "execution_ready", "execution_blockers", "verified_offer")}
            for p in products],
    }
    return radar, private


def run():
    init_db().close()
    config = load_config()
    portfolio = load_portfolio()
    state = capital_state(config)

    enabled = config.get("enabled_sources", {})
    # Aucun montant dans les logs (logs Actions publics sur depot public).
    print(f"[config] capital : {'renseigne' if state['capital_known'] else 'NON renseigne (execution bloquee)'}", flush=True)
    if state["config_errors"]:
        print(f"[config] ERREURS : {state['config_errors']} -> aucune execution autorisee", flush=True)
    print(f"[config] sources actives : {[k for k, v in enabled.items() if v]}", flush=True)
    print(f"[config] sources desactivees : {[k for k, v in enabled.items() if not v]}", flush=True)

    results = []
    snaps = {}
    trends_signals = []
    reddit_signals = []
    scavio_offers = []
    scavio_by_id = {}
    sources_failed = set()
    products = []

    # --- Section 1 : Watchlist principale (prix) ---
    print("\n[main] === section prix ===", flush=True)
    for item in WATCHLIST:
        if not _is_enabled(config, item["source"]):
            print(f"[{item['source']}] {item['id']} : source desactivee", flush=True)
            products.append(_failure_product(item, "NO_DATA", "source desactivee"))
            continue
        try:
            snap = fetch_one(item)
            if not snap:
                print(f"[{item['source']}] {item['id']} : aucun resultat", flush=True)
                products.append(_failure_product(item, "NO_DATA", "aucun resultat"))
                continue
            snap["product_id"] = item["id"]
            results.append(snap)
            snaps[item["id"]] = snap
        except Exception as e:
            msg = redact(e)
            print(f"[{item['source']}] {item['id']} ERREUR : {msg}", flush=True)
            sources_failed.add(item["source"])
            products.append(_failure_product(item, "ERROR", msg))

    # --- Section 2 : Google Trends ---
    print("\n[trends] === section Google Trends ===", flush=True)
    if not _is_enabled(config, "trends"):
        print("[trends] source desactivee dans config.json, section ignoree", flush=True)
    else:
        for item in _get_trends_watch():
            try:
                trend = fetch_trends_spy(item["keyword"])
                if trend:
                    trend["product_id"] = item["id"]
                    results.append(trend)
                    trends_signals.append({
                        "id": item["id"], "keyword": item["keyword"],
                        "acceleration": trend.get("trend_acceleration"),
                        "recent_avg": trend["trend_recent_avg"],
                        "older_avg": trend["trend_older_avg"],
                        "statut": trend.get("trend_statut", ""),
                    })
            except Exception as e:
                sources_failed.add("trends")
                print(f"[trends] {item['id']} ERREUR : {redact(e)}", flush=True)

    # --- Section 3 : Reddit ---
    print("\n[reddit] === section Reddit ===", flush=True)
    if not _is_enabled(config, "reddit"):
        print("[reddit] source desactivee dans config.json, section ignoree", flush=True)
    else:
        for item in _get_reddit_watch():
            try:
                snap = fetch_reddit(item["subreddit"], item["query"], limit=25)
                if snap:
                    snap["product_id"] = item["id"]
                    results.append(snap)
                    reddit_signals.append({
                        "id": item["id"], "subreddit": item["subreddit"],
                        "query": item["query"],
                        "total": snap["reddit_total"],
                        "recent_30d": snap["reddit_recent_30d"],
                        "avg_score": snap["reddit_avg_score"],
                        "avg_comments": snap["reddit_avg_comments"],
                    })
            except Exception as e:
                sources_failed.add("reddit")
                print(f"[reddit] {item['id']} ERREUR : {redact(e)}", flush=True)

    # --- Section 4 : Scavio (offres retail FR) ---
    print("\n[scavio] === section Scavio Google Shopping ===", flush=True)
    if not _is_enabled(config, "scavio"):
        print("[scavio] source desactivee dans config.json, section ignoree", flush=True)
    else:
        for item in SCAVIO_WATCH:
            try:
                snap = fetch_scavio_offers(item["query"], gl="fr", hl="fr",
                                           limit=10, raise_errors=True)
                if snap:
                    entry = {"id": item["id"], "query": item["query"],
                             "n_offers": snap["n_offers"],
                             "min_price_eur": snap["min_price_eur"],
                             "offers": snap["offers"][:5]}
                    scavio_offers.append(entry)
                    scavio_by_id[item["id"]] = {**entry, "offers": snap["offers"]}
                    print(f"[scavio] {item['id']} : {snap['n_offers']} offres", flush=True)
                else:
                    print(f"[scavio] {item['id']} : aucun resultat", flush=True)
            except Exception as e:
                sources_failed.add("scavio")
                print(f"[scavio] {item['id']} ERREUR : {redact(e)}", flush=True)

    # --- Section 5 : Decisions (capital-independantes) + financement ---
    digest = []
    order = {it["id"]: i for i, it in enumerate(WATCHLIST)}
    for item in WATCHLIST:
        if item["id"] not in snaps:
            continue
        offer = match_verified_offer(item, scavio_by_id.get(scavio_id_for(item["id"])))
        p = evaluate_product(item, snaps[item["id"]], config, offer)
        products.append(p)
        print(f"[{item['source']}] {item['id']} : {p.get('message', p['decision'])}", flush=True)
        if p["price_eur"] is not None:
            digest.append({"id": item["id"], "niveau": p["decision"],
                           "prix_eur": p["price_eur"], "source": item["source"]})
        if p["opportunity_alert"]:
            # L'alerte ne contient aucune donnee de capital.
            send_message(format_alert(item, p["price_eur"], p["decision"], snaps[item["id"]]))
    products.sort(key=lambda p: order.get(p["id"], 1e9))

    # --- Section 6 : Ecriture radar.json (public) + rapport prive ---
    generated_at = datetime.now(timezone.utc).isoformat()
    radar, private = build_outputs(products, config, sources_failed,
                                   trends_signals, reddit_signals,
                                   scavio_offers, generated_at)
    atomic_write_json("radar.json", radar)
    atomic_write_json(PRIVATE_OUTPUT, private)
    print("\nradar.json ecrit (sans donnees financieres privees)", flush=True)

    if results:
        insert_snapshots([_flatten(r) for r in results])
        print(f"{len(results)} snapshots inseres dans storage.db", flush=True)

    send_daily_digest(digest, radar["summary"])

    s = radar["summary"]
    print("\n=== RESUME ===", flush=True)
    print(f"statut donnees : {s['data_status']} (couverture {s['coverage']:.0%})", flush=True)
    print(f"posture : {s['posture']} -> {s['decision']}", flush=True)


def _flatten(s):
    return (s["product_id"], s["source"], s["captured_at"],
            s.get("sold_price_avg"), s.get("sold_price_median"),
            s.get("sold_count_30d"), s.get("active_listings"),
            s.get("sell_through"), s.get("lowest_ask"),
            s.get("currency"), s.get("raw_json"))


if __name__ == "__main__":
    run()