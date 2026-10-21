"""Adaptateurs de sources pour Discovery.

Contrat : search(query, limit) -> list[observation]
  - leve une exception en cas d'echec technique (jamais de liste vide
    silencieuse sur erreur) ;
  - liste vide = la source a repondu sans resultat.
Les adaptateurs reutilisent les connecteurs existants (connectors/*).
"""
import hashlib
import json
import os
from datetime import datetime, timezone


class SourceUnavailable(RuntimeError):
    """Identifiants ou module absents : la source n'a pas ete interrogee."""


def _ext_id(*parts):
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


class FixtureAdapter:
    """Donnees hors reseau, pour tests et demonstrations.

    Toute observation porte simulated=True : elle ne doit jamais etre
    presentee comme une collecte reelle.
    """
    cost_per_call = 0

    def __init__(self, path, name="fixture"):
        self.name = name
        with open(path, encoding="utf-8") as f:
            self._data = json.load(f)

    def search(self, query, limit=20):
        entry = self._data.get(query)
        if entry == "__ERROR__":
            raise RuntimeError(f"erreur simulee pour '{query}'")
        out = []
        for obs in (entry or [])[:limit]:
            o = dict(obs)
            o.setdefault("source", self.name)
            o["simulated"] = True
            out.append(o)
        return out


class ScavioRetailAdapter:
    """Offres boutique FR (Google Shopping via Scavio) -> RETAIL_OFFER."""
    name = "scavio_retail_fr"
    cost_per_call = 1

    def search(self, query, limit=10):
        from connectors.scavio import fetch_scavio_offers, SCAVIO_AVAILABLE, SCAVIO_API_KEY
        if not SCAVIO_AVAILABLE or not SCAVIO_API_KEY:
            raise SourceUnavailable("scavio indisponible (module ou cle absente)")
        snap = fetch_scavio_offers(query, gl="fr", hl="fr", limit=limit, raise_errors=True)
        if not snap:
            return []
        now = snap.get("captured_at") or datetime.now(timezone.utc).isoformat()
        out = []
        for o in snap["offers"]:
            if o.get("price_eur") is None or not o.get("product_link"):
                continue
            out.append({
                "source": self.name,
                "source_url": o["product_link"],
                "external_id": o.get("catalog_id") or _ext_id(o["product_link"]),
                "observed_at": now,
                "name": o.get("title") or "",
                "price_eur": o["price_eur"],
                "evidence_type": "RETAIL_OFFER",
                "seller": o.get("seller"),
                "seller_type": "PRO",
                "market": "FR",
            })
        return out


class EbaySoldAdapter:
    """Ventes conclues eBay (Apify) -> SOLD. Conversion USD explicite."""
    name = "ebay_sold"
    cost_per_call = 1
    paid = True  # acteur tiers facture a l'usage : soumis a l'entonnoir

    def __init__(self, usd_to_eur=None, spend_guard=None):
        self.usd_to_eur = usd_to_eur
        self.spend_guard = spend_guard

    def search(self, query, limit=50):
        # Double verrou : meme appelee directement (hors PaidGate), la source
        # payante exige l'accord du garde de depense.
        if self.spend_guard is None:
            from investigation.spend import SpendNotAuthorized
            raise SpendNotAuthorized("aucun garde de depense : appel payant refuse")
        if not os.environ.get("APIFY_TOKEN"):
            raise SourceUnavailable("APIFY_TOKEN absent")
        if not self.usd_to_eur:
            raise SourceUnavailable("taux USD->EUR non fourni")
        from connectors.ebay import fetch_sold_items
        # Exige une reservation active (posee par PaidGate) : consomme sans
        # re-debiter. Un appel direct ou une reservation reutilisee est refuse.
        self.spend_guard.consume(self.name, query)
        out = []
        for it in fetch_sold_items(query, count=limit):
            try:
                price = float(it["soldPrice"])
            except (KeyError, TypeError, ValueError):
                continue
            cur = (it.get("soldCurrency") or "USD").upper()
            if cur not in ("USD", "EUR"):
                continue
            fx = 1.0 if cur == "EUR" else self.usd_to_eur
            iid = it.get("itemId")
            url = it.get("url") or it.get("itemUrl") or (f"https://www.ebay.com/itm/{iid}" if iid else None)
            ended = it.get("endedAt")
            if not url or not ended:
                continue
            if "T" in ended and not ended.endswith("Z") and "+" not in ended[10:]:
                ended = ended + "Z"
            out.append({
                "source": self.name, "source_url": url,
                "external_id": iid or _ext_id(url, ended),
                "observed_at": ended, "name": it.get("title") or "",
                "price_eur": round(price * fx, 2), "currency_src": cur,
                "fx_rate": fx, "evidence_type": "SOLD",
                "condition": it.get("condition"), "market": "EBAY_US",
            })
        return out
