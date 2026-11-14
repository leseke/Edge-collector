"""Import d'un lot de preuves -> magasin append-only -> qualification -> corpus reel.

python -m intelligence.evidence_import --batch <lot.json> --store <dossier> \
    --spec <market_spec.json> --corpus-out <corpus.json> --now ISO
Idempotent : relancer le meme lot n'ajoute rien. Aucun reseau.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

from edge_io import atomic_write_json
from intelligence.corpus import load_corpus_dict
from intelligence.evidence import EvidenceStore, build_corpus, qualify


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True)
    ap.add_argument("--store", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--corpus-out", required=True)
    ap.add_argument("--now")
    a = ap.parse_args(argv)
    now = datetime.fromisoformat(a.now) if a.now else datetime.now(timezone.utc)
    with open(a.batch, encoding="utf-8") as f:
        batch = json.load(f)
    if batch.get("simulated") is not False:
        print("REFUSE : lot non declare reel (simulated != false)")
        return 1
    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    store = EvidenceStore(a.store)
    res = store.import_batch(batch["items"], batch_id=batch["batch_id"], now=now)
    print(f"Import : {res['accepted']} accepte(s), {res['duplicates']} doublon(s), {res['changed']} page(s) modifiee(s), "
          f"{len(res['rejected'])} rejete(s)")
    for r in res["rejected"]:
        print("  REJET", r["index"], r["errors"])
    items = store.items()
    q = qualify(items, now=now, required_topics=[t["topic_id"] for t in spec["topics"]])
    atomic_write_json(os.path.join(a.store, "qualification.json"), q)
    print(f"Qualification : {len(q['mirrors'])} miroir(s), {len(q['contradictions'])} contradiction(s), "
          f"{len(q['stale_measurements'])} mesure(s) ancienne(s), sujets sans donnee : {q['insufficient_topics']}")
    for r in q["insufficient_reasons"]:
        print("  -", r)
    corpus = build_corpus(items, spec, data_as_of=max(i["observed_at"] for i in items))
    load_corpus_dict(corpus)  # validation EDGE complete
    atomic_write_json(a.corpus_out, corpus)
    print(f"Corpus reel : {a.corpus_out} ({len(corpus['sources'])} sources, {len(corpus['extracts'])} extraits, "
          f"{len(corpus['datasets'])} series)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
