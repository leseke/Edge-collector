"""AI-002D: conservative, opt-in snapshot monitor for allowlisted public documents.

No implicit network, no scraping of prices, no external AI. A fixture transport can
be used to exercise the same capture path without a network. Snapshots retain
observed date and digest; changes are content changes, never inferred sales.
"""
import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit

from intelligence.evidence import _append_line

ALLOWLIST = {"www.pokemon.cn"}
MAX_BYTES = 350_000


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.fragments = []
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.skip:
            self.skip -= 1
    def handle_data(self, data):
        if not self.skip and data.strip():
            self.fragments.append(data.strip())


def visible_text(raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise ValueError("document absent ou trop volumineux")
    p = _VisibleText()
    p.feed(raw.decode("utf-8", errors="replace"))
    return re.sub(r"\s+", " ", unescape(" ".join(p.fragments))).strip()


def validate_url(url):
    p = urlsplit(url)
    if p.scheme != "https" or p.hostname not in ALLOWLIST or p.username or p.password or p.port not in (None, 443):
        raise ValueError("source interdite ou URL invalide")
    if not (p.path == "/tcg" or p.path.startswith("/tcg/")):
        raise ValueError("page hors rubrique Pokémon TCG")
    if p.query or p.fragment:
        raise ValueError("URL canonique requise")
    return url


class SnapshotMonitor:
    def __init__(self, root, fetch):
        self.root = root
        self.ledger = os.path.join(root, "snapshots.jsonl")
        self.fetch = fetch

    def history(self, url=None):
        if not os.path.exists(self.ledger):
            return []
        records = []
        with open(self.ledger, encoding="utf-8") as fh:
            for line in fh:
                if not line.endswith("\n"):
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if url is None or row.get("url") == url:
                    records.append(row)
        return records

    def capture(self, url, observed_at, allow_network=False):
        validate_url(url)
        if not isinstance(observed_at, datetime) or observed_at.tzinfo is None:
            raise ValueError("date timezone-aware obligatoire")
        if allow_network is not True:
            raise PermissionError("capture non autorisée explicitement")
        raw = self.fetch(url)
        text = visible_text(raw)
        if len(text) < 40:
            raise ValueError("contenu insuffisant, aucune observation publiée")
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        earlier = self.history(url)
        if earlier and observed_at.isoformat() < earlier[-1]["observed_at"]:
            raise ValueError("observations hors ordre chronologique")
        if earlier and earlier[-1]["sha256"] == sha:
            status = "unchanged"
        elif earlier:
            status = "changed"
        else:
            status = "first_observation"
        row = {"schema": "edge.market_snapshot.v1", "url": url,
               "observed_at": observed_at.isoformat(), "sha256": sha,
               "status": status, "previous_sha256": earlier[-1]["sha256"] if earlier else None,
               "text_length": len(text), "source_kind": "official_site_public_page",
               "verification": "unverified", "data_type": "page_content_not_sales",
               "rights": "unknown", "note": "variation de page, pas mesure de popularité ou de ventes"}
        os.makedirs(self.root, exist_ok=True)
        # Unexpectedly truncated tails are isolated before append (never rewritten).
        if os.path.exists(self.ledger) and os.path.getsize(self.ledger):
            with open(self.ledger, "rb") as f:
                f.seek(-1, 2)
                truncated = f.read(1) != b"\n"
            if truncated:
                _append_line(self.ledger, "")
        _append_line(self.ledger, json.dumps(row, sort_keys=True, ensure_ascii=False))
        return row


def safe_http_fetch(url):
    """Opt-in only; requests redirect handling disabled to prevent off-list redirects."""
    import requests
    validate_url(url)
    r = requests.get(url, timeout=12, allow_redirects=False, headers={"User-Agent": "EDGE-research-monitor/0.1"})
    if r.status_code != 200:
        raise ValueError(f"statut HTTP {r.status_code}; aucune publication")
    if "text/html" not in r.headers.get("Content-Type", ""):
        raise ValueError("réponse non HTML")
    if len(r.content) > MAX_BYTES:
        raise ValueError("taille dépassée")
    return r.content


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="https://www.pokemon.cn/tcg")
    p.add_argument("--store", required=True)
    p.add_argument("--allow-live-fetch", action="store_true")
    a = p.parse_args(argv)
    if not a.allow_live_fetch:
        p.error("capture désactivée : --allow-live-fetch requis")
    monitor = SnapshotMonitor(a.store, safe_http_fetch)
    print(json.dumps(monitor.capture(a.url, datetime.now(timezone.utc), allow_network=True), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
