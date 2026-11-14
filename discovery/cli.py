"""Lancement d'un pipeline Discovery.

Demo hors reseau (fixtures fictives) :
  python -m discovery.cli --campaigns discovery/demo_campaigns.json \
      --fixtures discovery/fixtures/demo_observations.json \
      --as-of 2026-10-18T09:00:00+00:00 --out-dir /tmp/edge-demo

Reel (identifiants requis : SCAVIO_API_KEY, APIFY_TOKEN) :
  python -m discovery.cli --campaigns discovery/campaigns.json --out-dir data/discovery
"""
import argparse
import json
import os
from datetime import datetime, timezone

from discovery.adapters import EbaySoldAdapter, FixtureAdapter, ScavioRetailAdapter
from discovery.campaigns import load_campaigns
from discovery.pipeline import run_pipeline
from edge_engine import load_config


def watchlist_keys():
    from collect import WATCHLIST
    keys = []
    for it in WATCHLIST:
        nums = [m for m in it.get("must_all", []) if m.isdigit()]
        if nums and it["id"].startswith("lego_"):
            keys.append(f"lego:{nums[0]}")
    return keys


def _official(http, environ, usd_to_eur, as_of=None):
    """as_of : date de reference d'un rejeu. Les observations sont alors
    datees a as_of (et non a l'horloge murale), sinon un rejeu effectue un
    autre jour produit des observations "du futur" et fausse la fraicheur."""
    from discovery.adapters_official import (BrickLinkAdapter, BricksetAdapter,
                                             EbayBrowseAdapter, TcgdexAdapter)
    now = (lambda: as_of.isoformat()) if as_of else None
    clock = (lambda: as_of) if as_of else None
    return {"ebay_browse": EbayBrowseAdapter(http=http, environ=environ, now=now),
            "bricklink": BrickLinkAdapter(http=http, environ=environ, now=now),
            "brickset": BricksetAdapter(http=http, environ=environ, now=now),
            "tcgdex": TcgdexAdapter(http=http, max_details=2, clock=clock)}


class _NoPaidFixture:
    """Source payante simulee pour le pilote : ne renvoie rien. Elle sert a
    verifier que l'entonnoir bloque tout appel non autorise."""
    name = "ebay_sold"
    paid = True
    cost_per_call = 1

    def search(self, query, limit=20):
        return []


def build_adapters(fixtures=None, usd_to_eur=None, offline_http=None, registry=None, environ=None,
                   spend_guard=None, as_of=None):
    """spend_guard : SpendGuard construit depuis config.private.json. Sans
    lui, la source payante est enveloppee par un garde sans autorisation."""
    from discovery.access import GatedAdapter, load_registry
    from investigation.spend import PaidGate, SpendGuard
    guard = spend_guard if spend_guard is not None else SpendGuard(None)
    if fixtures:
        # Mode demo : toutes les sources sont servies par les fixtures
        # (observations marquees simulated=True).
        fa = FixtureAdapter(fixtures)
        return {"fixture": fa, "scavio_retail_fr": fa, "ebay_sold": fa}
    reg = registry or load_registry()
    if offline_http:
        # Pilote hors reseau : formats d'API rejoues depuis des fixtures.
        # Le registre est force a VERIFIED EN MEMOIRE uniquement, avec des
        # identifiants factices : rien n'est ecrit, rien n'est appele.
        from discovery.fixture_http import FixtureTransport, SimulatedMarker
        http = FixtureTransport(offline_http)
        fake_env = {v: "fixture" for s in reg.values() for v in s.get("env", [])}
        reg = {k: dict(v, status="VERIFIED") for k, v in reg.items()}
        inner = {**_official(http, fake_env, usd_to_eur, as_of)}
        out = {k: GatedAdapter(k, SimulatedMarker(v), reg, fake_env) for k, v in inner.items()}
        out["ebay_sold"] = PaidGate("ebay_sold", GatedAdapter("ebay_sold", SimulatedMarker(_NoPaidFixture()),
                                                              reg, fake_env), guard)
        return out
    # Reel : chaque source passe par le registre (conditions verifiees +
    # identifiants presents), sinon SKIPPED_UNAVAILABLE explicite.
    inner = {**_official(None, environ, usd_to_eur), "scavio_retail_fr": ScavioRetailAdapter()}
    out = {k: GatedAdapter(k, v, reg, environ) for k, v in inner.items()}
    # Double verrou : PaidGate (couche d'execution) + garde exige par l'adaptateur.
    out["ebay_sold"] = PaidGate("ebay_sold", GatedAdapter(
        "ebay_sold", EbaySoldAdapter(usd_to_eur, spend_guard=guard), reg, environ), guard)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaigns", required=True)
    ap.add_argument("--only", nargs="*", help="ids de campagnes a executer")
    ap.add_argument("--fixtures")
    ap.add_argument("--offline-http", help="pilote hors reseau : fichier de routes HTTP fictives")
    ap.add_argument("--as-of")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--private-dir", default=None)
    ap.add_argument("--usd-to-eur", type=float, default=None)
    ap.add_argument("--strategy", default="FLIP", choices=["FLIP", "FUTURE_CLASSIC"])
    ap.add_argument("--max-total-calls", type=int, default=None,
                    help="plafond global d'appels payants pour ce run (pilote)")
    ap.add_argument("--plan-only", action="store_true",
                    help="affiche les appels prevus et leur cout maximal, sans rien interroger")
    a = ap.parse_args(argv)
    config = load_config()
    camps = load_campaigns(a.campaigns)
    if a.only:
        camps = [c for c in camps if c["id"] in a.only]
    if a.plan_only:
        total = 0
        for c in camps:
            if not c.get("enabled", True):
                continue
            if c.get("queries_from") == "store_revalidation":
                n_q = max(1, c.get("max_calls", 10) // max(1, len(c["sources"])))
            else:
                n_q = len(c.get("queries", []))
            base = n_q * len(c["sources"])
            exp = c.get("max_expansions", 0) * len(c.get("expansion_sources", c["sources"]))
            mx = min(c.get("max_calls", 10), base + exp)
            total += mx
            dropped = max(0, base - c.get("max_calls", 10))
            note = f" ({dropped} appel(s) initiaux NON executes : budget)" if dropped else ""
            print(f"{c['id']:<28} {c['family']:<14} appels initiaux {base:>2} + expansion <= {exp:>2} -> plafond {mx}{note}")
        cap = min(total, a.max_total_calls) if a.max_total_calls is not None else total
        print(f"Plafond d'appels pour ce run : {cap} (cout reel = appels x tarif de chaque source, a mesurer)")
        return {"planned_max_calls": cap}
    as_of = datetime.fromisoformat(a.as_of) if a.as_of else datetime.now(timezone.utc)
    usd = a.usd_to_eur or config.get("usd_to_eur")
    if not usd and not a.fixtures and not a.offline_http:
        # Repli sur le taux fixe historique de collect.py (0,92) : signale.
        from collect import USD_TO_EUR
        usd = USD_TO_EUR
        print(f"[discovery] taux USD->EUR fixe {usd} (collect.USD_TO_EUR) : a remplacer par un taux date", flush=True)
    private_dir = a.private_dir or os.path.join("private", "discovery")
    from investigation.spend import SpendGuard
    guard = SpendGuard.from_private_file(ledger_path=os.path.join("private", "spend_ledger.jsonl"))
    print(f"[depense] {guard.public_reason}", flush=True)  # logs Actions publics : aucun montant
    out, invs, _ = run_pipeline(
        camps, build_adapters(a.fixtures, usd, offline_http=a.offline_http, spend_guard=guard,
                       as_of=as_of if a.offline_http else None), config,
        store_dir=os.path.join(a.out_dir, "store"),
        public_path=os.path.join(a.out_dir, "latest.json"),
        private_dir=private_dir, as_of=as_of, watchlist_keys=watchlist_keys(),
        strategy=a.strategy, max_total_calls=a.max_total_calls,
        cost_journal_path=os.path.join(a.out_dir, "cost_journal.jsonl"), spend_guard=guard)
    print(json.dumps({"posture": out["posture"], "simulated": out["simulated"],
                      **out["summary"]}, ensure_ascii=False, indent=1))
    for p in out["products"]:
        inv = p.get("investigation")
        print(f"- {p['product_key']:<40} watchlist={p['in_watchlist']!s:<5} sold={p['n_sold']:<3} "
              f"{'-> ' + inv['decision'] + ' (' + inv['confidence'] + ')' if inv else '(pas d indice)'}")
    return out


if __name__ == "__main__":
    main()
