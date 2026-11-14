"""Poser une question a l'agent hors ligne.

python -m intelligence.ask "Analyse l'evolution de Pokemon en Chine..." \
    [--corpus intelligence/corpus] [--store private/intelligence_preview] [--now ISO]

Par defaut le rapport est ecrit dans un espace PRIVE (non publie). Publier
pour le dashboard exige --store data/intelligence (choix explicite).
"""
import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone

from intelligence.corpus import CorpusRejected, load_corpus
from intelligence.inquiry import run_inquiry
from intelligence.store import ReportStore
from intelligence.validator import assess


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--corpus", default=os.path.join("intelligence", "corpus"))
    ap.add_argument("--store", default=os.path.join("private", "intelligence_preview"))
    ap.add_argument("--now")
    ap.add_argument("--provider", default="offline", choices=["offline", "mock-openai", "openai"],
                    help="offline (defaut) | mock-openai (contrat OpenAI simule, aucun reseau) | openai (desactive par defaut)")
    ap.add_argument("--model", help="modele OpenAI explicite (obligatoire avec --provider openai)")
    a = ap.parse_args(argv)
    corpora, refused = [], []
    for f in sorted(glob.glob(os.path.join(a.corpus, "*.json"))):
        try:
            corpora.append(load_corpus(f))
        except CorpusRejected as e:
            refused.append(f"{os.path.basename(f)} : {e}")
    for r in refused:
        print("CORPUS REFUSE :", r)
    now = datetime.fromisoformat(a.now) if a.now else datetime.now(timezone.utc)
    provider, guard, send, max_ops = None, None, None, 1
    if a.provider != "offline":
        from intelligence.inquiry import report_id_for
        from intelligence.planner import plan_question
        from intelligence.providers.openai_responses import OpenAIResponsesProvider, make_http_send
        from investigation.spend import SpendGuard
        max_ops = 2  # plan + analyse : deux operations facturables, deux reservations
        if a.provider == "mock-openai":
            from intelligence.providers.mock_openai import MockResponsesAPI
            print("FOURNISSEUR SIMULE (mock) : aucun appel reseau, aucune depense reelle")
            provider = OpenAIResponsesProvider(model=a.model or "mock-model",
                                               environ={"EDGE_OPENAI_ENABLED": "1", "OPENAI_API_KEY": "mock"},
                                               registry={"openai": {"status": "VERIFIED"}})
            guard = SpendGuard({"authorized": True, "max_usd_per_run": 0.2, "est_usd_per_call": 0.1},
                               ledger_path=os.path.join("private", "mock_spend_ledger.jsonl"))
            send = MockResponsesAPI().send
        else:
            if not a.model:
                print("--model obligatoire avec --provider openai")
                return 1
            provider = OpenAIResponsesProvider(model=a.model)
            ok, why = provider.enabled()
            if not ok:
                print("REFUSE avant tout appel :", why)
                return 1
            guard = SpendGuard.from_private_file(ledger_path=os.path.join("private", "spend_ledger.jsonl"))
            print("[depense]", guard.public_reason)
            send = make_http_send(os.environ)
        plan = plan_question(a.question, corpora)
        if plan.get("status") == "OK":
            guard.allow([report_id_for(a.question, plan["corpus_id"])])
    res = run_inquiry(a.question, corpora, ReportStore(a.store), now=now, provider=provider,
                      spend_guard=guard, send=send, max_operations=max_ops)
    print("Statut :", res["status"])
    if res.get("plan"):
        p = res["plan"]
        if p.get("reason"):
            print("Raison :", p["reason"], p.get("candidates", ""))
        for sq in p.get("subquestions", []):
            print(f"  {sq['subquestion_id']} [{sq.get('status', '?')}] {sq['question']}")
    for v in res["violations"]:
        print("  VIOLATION :", v)
    if res["status"] == "REPORT":
        ev = assess(res["report"], now=now)
        print("Rapport :", res["entry"]["path"], "| dossier :", res["dossier_path"])
        print("Affichage :", ev["display_label"])
        print("Contradictions :", [c["assertion_key"] for c in res["dossier"]["contradictions"]])
        print("Extraits ecartes :", [e["extract_id"] for e in res["dossier"]["inventory"]["excluded_extracts"]])
    return 0 if res["status"] in ("REPORT", "NO_DATA", "AMBIGUOUS") else 1


if __name__ == "__main__":
    sys.exit(main())
