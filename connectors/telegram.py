import os, requests

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def send_message(text):
    if not TOKEN:
        print("[telegram] TOKEN absent", flush=True)
        return False
    if not CHAT_ID:
        print("[telegram] CHAT_ID absent", flush=True)
        return False
    print(f"[telegram] envoi vers chat {CHAT_ID}...", flush=True)
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15
        )
        print(f"[telegram] HTTP {r.status_code}", flush=True)
        if r.status_code != 200:
            print(f"[telegram] reponse : {r.text[:300]}", flush=True)
        return r.status_code == 200
    except Exception as e:
        print(f"[telegram] exception : {e}", flush=True)
        return False


def format_alert(item, prix_eur, niveau, snap):
    emoji = "🔥🔥" if niveau == "STRONG_BUY" else "🔥"
    cible = item.get("target_strong_buy") if niveau == "STRONG_BUY" \
            else item.get("target_buy")
    lines = [
        f"{emoji} <b>{niveau.replace('_', ' ')}</b>",
        f"<b>{item['id']}</b>",
        f"",
        f"Prix actuel : <b>{prix_eur:.0f} EUR</b>",
        f"Cible : {cible} EUR",
        f"Source : {item['source']}",
    ]
    return "\n".join(lines)


def send_daily_digest(watchlist_results):
    if not watchlist_results:
        print("[telegram] digest vide, rien a envoyer", flush=True)
        return
    lines = ["<b>EDGE - Resume</b>", ""]
    for r in watchlist_results:
        emoji = "⏸"
        if r["niveau"] == "STRONG_BUY":
            emoji = "🔥🔥"
        elif r["niveau"] == "BUY":
            emoji = "🔥"
        lines.append(
            f"{emoji} {r['id']} : {r['prix_eur']:.0f} EUR ({r['source']})"
        )
    lines.append("")
    n_buy = sum(1 for r in watchlist_results
                if r["niveau"] in ("BUY", "STRONG_BUY"))
    if n_buy == 0:
        lines.append("<b>Decision : CASH / ATTENDRE</b>")
    else:
        lines.append(f"<b>{n_buy} signal(aux) d'achat</b>")
    send_message("\n".join(lines))