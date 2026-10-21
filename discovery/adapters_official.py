"""Adaptateurs de sources officielles (eBay Browse, BrickLink, Brickset, TCGdex).

- Transport HTTP injectable (tests et pilote hors reseau via fixtures).
- Aucune valeur n'est completee : un champ absent rend l'observation
  incomplete et elle est ignoree ou rejetee a la normalisation.
- Les formats de reponse suivent la documentation publique ; ils DOIVENT
  etre confirmes au premier appel reel (cf. EDGE_SOURCES.md).
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import urllib.parse
from datetime import datetime, timezone

from discovery.adapters import SourceUnavailable
from discovery.identity import lego_set_numbers


class HttpError(RuntimeError):
    def __init__(self, status, detail=""):
        super().__init__(f"HTTP {status} {detail}"[:200])
        self.status = status


class RequestsTransport:
    """Transport reel (requests). Leve HttpError sur statut != 200."""

    def get(self, url, params=None, headers=None):
        import requests
        r = requests.get(url, params=params, headers=headers, timeout=30)
        if r.status_code != 200:
            raise HttpError(r.status_code)
        return r.json()

    def post(self, url, data=None, headers=None):
        import requests
        r = requests.post(url, data=data, headers=headers, timeout=30)
        if r.status_code != 200:
            raise HttpError(r.status_code)
        return r.json()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _has_single_set_number(query):
    return len(lego_set_numbers("lego " + query)) == 1


def _set_number(query):
    nums = lego_set_numbers("lego " + query)
    if len(nums) != 1:
        raise ValueError(f"requete sans numero de set unique : {query!r}")
    return nums[0]


# ------------------------------------------------------------------ eBay Browse

class EbayBrowseAdapter:
    """Annonces actives eBay (Browse API, search). Preuve : ASKING_PRICE.

    Ne fournit AUCUNE vente : les annonces servent a la prospection
    (offres potentiellement sous-evaluees), jamais a la valorisation.
    """
    name = "ebay_browse"
    cost_per_call = 0
    TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
    SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    SCOPE = "https://api.ebay.com/oauth/api_scope"

    def __init__(self, http=None, environ=None, marketplace="EBAY_FR", clock=time.time, now=None):
        self.http = http or RequestsTransport()
        self.env = os.environ if environ is None else environ
        self.marketplace = marketplace
        self.clock = clock
        self.now = now or _now
        self._token = None
        self._token_exp = 0

    def _access_token(self):
        if self._token and self.clock() < self._token_exp - 60:
            return self._token
        cid, sec = self.env.get("EBAY_CLIENT_ID"), self.env.get("EBAY_CLIENT_SECRET")
        if not cid or not sec:
            raise SourceUnavailable("EBAY_CLIENT_ID/EBAY_CLIENT_SECRET absents")
        basic = base64.b64encode(f"{cid}:{sec}".encode()).decode()
        res = self.http.post(self.TOKEN_URL,
                             data={"grant_type": "client_credentials", "scope": self.SCOPE},
                             headers={"Authorization": f"Basic {basic}",
                                      "Content-Type": "application/x-www-form-urlencoded"})
        self._token = res["access_token"]
        self._token_exp = self.clock() + int(res.get("expires_in", 7200))
        return self._token

    def search(self, query, limit=50):
        tok = self._access_token()
        res = self.http.get(self.SEARCH_URL,
                            params={"q": query, "limit": min(int(limit), 200),
                                    "filter": "conditionIds:{1000}"},  # 1000 = neuf
                            headers={"Authorization": f"Bearer {tok}",
                                     "X-EBAY-C-MARKETPLACE-ID": self.marketplace})
        now = self.now()
        out = []
        for it in res.get("itemSummaries", []) or []:
            price = (it.get("price") or {})
            if price.get("currency") != "EUR" or not it.get("itemWebUrl") or not it.get("itemId"):
                continue
            ship = None
            for so in it.get("shippingOptions") or []:
                sc = so.get("shippingCost") or {}
                if sc.get("currency") == "EUR" and sc.get("value") is not None:
                    v = float(sc["value"])
                    ship = v if ship is None else min(ship, v)
            seller = it.get("seller") or {}
            out.append({
                "source": self.name, "source_url": it["itemWebUrl"],
                "external_id": it["itemId"], "observed_at": now,
                "name": it.get("title") or "", "price_eur": float(price["value"]),
                "shipping_eur": ship, "evidence_type": "ASKING_PRICE",
                "condition": "new" if str(it.get("conditionId")) == "1000" else it.get("condition"),
                "seller": seller.get("username"),
                "seller_type": "UNKNOWN",  # le resume de recherche ne dit pas pro/particulier
                "seller_feedback_pct": seller.get("feedbackPercentage"),
                "market": self.marketplace,
                "buying_options": it.get("buyingOptions"),
            })
        return out


# ------------------------------------------------------------------ BrickLink

def _oauth1_header(method, url, params, ck, cs, tk, ts, nonce=None, timestamp=None):
    """Signature OAuth 1.0 HMAC-SHA1 (RFC 5849), sans dependance externe."""
    enc = lambda x: urllib.parse.quote(str(x), safe="~")
    oauth = {"oauth_consumer_key": ck, "oauth_token": tk,
             "oauth_signature_method": "HMAC-SHA1",
             "oauth_timestamp": str(timestamp or int(time.time())),
             "oauth_nonce": nonce or secrets.token_hex(8), "oauth_version": "1.0"}
    allp = {**(params or {}), **oauth}
    norm = "&".join(f"{enc(k)}={enc(v)}" for k, v in sorted(allp.items()))
    base = "&".join([method.upper(), enc(url), enc(norm)])
    key = f"{enc(cs)}&{enc(ts)}"
    sig = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    oauth["oauth_signature"] = sig
    return "OAuth " + ", ".join(f'{k}="{enc(v)}"' for k, v in sorted(oauth.items()))


class BrickLinkAdapter:
    """Guide des prix BrickLink, ventes des 6 derniers mois, NEUF.
    Preuve : SOLD_AGGREGATE (statistiques, pas des ventes individuelles)."""
    name = "bricklink"
    cost_per_call = 0
    BASE = "https://api.bricklink.com/api/store/v1"
    PERIOD_DAYS = 182  # "6 derniers mois" selon le guide des prix

    @staticmethod
    def accepts(query):
        """Ne traite que les requetes portant un numero de set unique."""
        return _has_single_set_number(query)

    def __init__(self, http=None, environ=None, region="europe", currency="EUR", now=None):
        self.http = http or RequestsTransport()
        self.env = os.environ if environ is None else environ
        self.region = region
        self.currency = currency
        self.now = now or _now

    def search(self, query, limit=1):
        keys = ("BRICKLINK_CONSUMER_KEY", "BRICKLINK_CONSUMER_SECRET",
                "BRICKLINK_TOKEN", "BRICKLINK_TOKEN_SECRET")
        if any(not self.env.get(k) for k in keys):
            raise SourceUnavailable("identifiants BrickLink absents")
        num = _set_number(query)
        url = f"{self.BASE}/items/SET/{num}-1/price"
        params = {"guide_type": "sold", "new_or_used": "N",
                  "region": self.region, "currency_code": self.currency}
        auth = _oauth1_header("GET", url, params, *(self.env[k] for k in keys))
        res = self.http.get(url, params=params, headers={"Authorization": auth})
        meta = res.get("meta") or {}
        if meta.get("code") != 200:
            raise HttpError(meta.get("code"), meta.get("message", ""))
        d = res.get("data") or {}
        if d.get("currency_code") != "EUR" or d.get("new_or_used") != "N":
            return []
        total_q = int(d.get("total_quantity") or 0)
        if total_q == 0:
            return []  # aucune vente : pas d'observation (et pas d'invention)
        now = self.now()
        return [{
            "source": self.name,
            "source_url": f"https://www.bricklink.com/v2/catalog/catalogitem.page?S={num}-1#T=P",
            "external_id": f"SET-{num}-1:sold:N:{self.region}:{now[:10]}",
            "observed_at": now, "name": f"LEGO {num}",
            "product_key": f"lego:{num}",
            "price_eur": float(d["qty_avg_price"]),
            "evidence_type": "SOLD_AGGREGATE",
            "aggregate": {
                "period_days": self.PERIOD_DAYS, "total_quantity": total_q,
                "lots": int(d.get("unit_quantity") or 0),
                "avg_price_eur": float(d["avg_price"]),
                "qty_avg_price_eur": float(d["qty_avg_price"]),
                "min_price_eur": float(d["min_price"]), "max_price_eur": float(d["max_price"]),
                "condition": "NEW", "region": self.region, "guide": "sold",
            },
        }]


# ------------------------------------------------------------------ Brickset

class BricksetAdapter:
    """Disponibilite commerciale (Brickset API v3, getSets). Preuve :
    AVAILABILITY (prix boutique, dates de premiere/derniere disponibilite)."""
    name = "brickset"
    cost_per_call = 0
    URL = "https://brickset.com/api/v3.asmx/getSets"

    @staticmethod
    def accepts(query):
        """Ne traite que les requetes portant un numero de set unique."""
        return _has_single_set_number(query)

    def __init__(self, http=None, environ=None, region="DE", now=None):
        # DE sert d'approximation europeenne (la zone FR n'est pas exposee
        # dans les champs documentes) : signale dans l'observation.
        self.http = http or RequestsTransport()
        self.env = os.environ if environ is None else environ
        self.region = region
        self.now = now or _now

    def search(self, query, limit=1):
        key = self.env.get("BRICKSET_API_KEY")
        if not key:
            raise SourceUnavailable("BRICKSET_API_KEY absent")
        num = _set_number(query)
        res = self.http.get(self.URL, params={"apiKey": key, "userHash": "",
                                              "params": json.dumps({"setNumber": f"{num}-1"})})
        if res.get("status") != "success":
            raise HttpError(200, f"brickset status={res.get('status')} {res.get('message', '')}")
        now = self.now()
        out = []
        for s in res.get("sets") or []:
            if str(s.get("number")) != num:
                continue
            reg = ((s.get("LEGOCom") or {}).get(self.region) or {})
            out.append({
                "source": self.name,
                "source_url": f"https://brickset.com/sets/{num}-{s.get('numberVariant', 1)}",
                "external_id": f"{num}-{s.get('numberVariant', 1)}:{self.region}:{now[:10]}",
                "observed_at": now, "name": f"LEGO {num} {s.get('name', '')}".strip(),
                "product_key": f"lego:{num}", "evidence_type": "AVAILABILITY",
                "availability": {"region": self.region,
                                 "retail_price_eur": reg.get("retailPrice"),
                                 "date_first": reg.get("dateFirstAvailable"),
                                 "date_last": reg.get("dateLastAvailable")},
                "theme": s.get("theme"), "year": s.get("year"),
            })
        return out


# ------------------------------------------------------------------ TCGdex

# Schema documente (https://tcgdex.dev/markets-prices) : pricing.cardmarket
# porte des champs standard et leurs equivalents "-holo". Chaque variante
# est un produit distinct. Le fournisseur est omis si la carte n'y est pas.
CARDMARKET_FIELDS = ("avg", "low", "trend", "avg1", "avg7", "avg30")
CARDMARKET_VARIANTS = {"normal": "", "holo": "-holo"}


def validate_card_pricing(card):
    """Controle de schema d'une reponse carte. Retourne une liste
    d'anomalies (vide = conforme). N'invente ni ne corrige aucune valeur."""
    issues = []
    if not isinstance(card, dict) or not card.get("id"):
        return ["carte sans identifiant"]
    pricing = card.get("pricing")
    if pricing is None:
        return ["pricing absent (carte sans donnees de marche)"]
    cm = pricing.get("cardmarket")
    if cm is None:
        return ["pricing.cardmarket absent (carte non listee sur Cardmarket)"]
    if cm.get("unit") != "EUR":
        issues.append(f"devise inattendue : {cm.get('unit')!r}")
    upd = cm.get("updated")
    try:
        datetime.fromisoformat(str(upd).replace("Z", "+00:00"))
    except ValueError:
        issues.append(f"date updated illisible : {upd!r}")
    known = {"updated", "unit", *CARDMARKET_FIELDS, *(f + "-holo" for f in CARDMARKET_FIELDS)}
    unknown = sorted(set(cm) - known)
    if unknown:
        issues.append(f"champs non documentes : {unknown}")
    for var, suf in CARDMARKET_VARIANTS.items():
        vals = {f: cm.get(f + suf) for f in CARDMARKET_FIELDS}
        present = {k: v for k, v in vals.items() if v is not None}
        if not present:
            continue
        for k, v in present.items():
            if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
                issues.append(f"{var}.{k} non numerique ou negatif : {v!r}")
        if vals["trend"] in (None, 0):
            issues.append(f"{var}.trend absent ou nul")
    return issues


class TcgdexAdapter:
    """Prix Cardmarket indicatifs de cartes Pokemon a l'unite (TCGdex).
    Preuve : MARKET_TREND, une observation PAR VARIANTE (normal / holo).
    Ne couvre PAS les produits scelles. Jamais une vente."""
    name = "tcgdex"
    cost_per_call = 0
    BASE = "https://api.tcgdex.net/v2/en"

    def __init__(self, http=None, max_details=2, stale_after_days=7, clock=None):
        self.http = http or RequestsTransport()
        self.max_details = max_details
        self.stale_after_days = stale_after_days
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.http_calls = 0

    def _get(self, url, params=None):
        self.http_calls += 1
        return self.http.get(url, params=params)

    def search(self, query, limit=2):
        n = max(1, min(int(limit), self.max_details))
        # Sans pagination l'API renvoie TOUTES les cartes correspondantes :
        # une seule page courte, conformement a l'usage raisonnable demande.
        cards = self._get(f"{self.BASE}/cards",
                          params={"name": query, "pagination:page": 1,
                                  "pagination:itemsPerPage": n}) or []
        now = self.clock()
        out = []
        for c in cards[:n]:
            cid = c.get("id")
            if not cid:
                continue
            d = self._get(f"{self.BASE}/cards/{urllib.parse.quote(cid)}")
            issues = validate_card_pricing(d)
            cm = ((d.get("pricing") or {}).get("cardmarket")) or {}
            if cm.get("unit") != "EUR":
                continue  # devise absente ou autre : aucune supposition
            try:
                updated = datetime.fromisoformat(str(cm.get("updated")).replace("Z", "+00:00"))
            except ValueError:
                continue  # date illisible : fraicheur inconnue -> pas d'observation
            age = (now - updated).days
            for var, suf in CARDMARKET_VARIANTS.items():
                trend = cm.get("trend" + suf)
                if isinstance(trend, bool) or not isinstance(trend, (int, float)) or trend <= 0:
                    continue  # variante sans prix : pas d'observation
                out.append({
                    "source": self.name,
                    "source_url": f"https://api.tcgdex.net/v2/en/cards/{cid}",
                    "external_id": f"{cid}:{var}:{updated.date().isoformat()}",
                    # date du prix chez le fournisseur, pas date de collecte
                    "observed_at": updated.isoformat(),
                    "name": f"Pokemon card {d.get('name', '')} {cid} {var}",
                    "product_key": f"tcg:pokemon:{cid}:{var}",
                    "price_eur": float(trend), "evidence_type": "MARKET_TREND",
                    "condition": "new",
                    "market_stats": {"variant": var, "updated": cm.get("updated"),
                                     "age_days": age, "stale": age > self.stale_after_days,
                                     **{k: cm.get(k + suf) for k in CARDMARKET_FIELDS}},
                    "schema_issues": issues,
                    "caveat": ("prix indicatif Cardmarket (tendance), pas une vente ; "
                               "correspondance variante/annonce non garantie par la source"),
                })
        return out
